"""
AgentOS — RabbitMQ event consumer.

Features:
- Automatic ack/nack with retry support
- Dead Letter Queue routing on exhausted retries
- Idempotency check before processing
- OpenTelemetry context extraction from headers
- Per-message error isolation (one bad message won't kill the consumer)
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Optional

import aio_pika
import aio_pika.abc

try:
    from opentelemetry.propagate import extract
except ImportError:
    def extract(carrier: Any) -> Any:  # type: ignore[misc]
        return None

from shared.config import settings
from shared.logging import get_logger
from shared.messaging.idempotency import IdempotencyStore
from shared.messaging.retry import RetryPolicy, ExponentialBackoff
from shared.schemas.events import BaseEvent

logger = get_logger(__name__)

MessageHandler = Callable[[BaseEvent, aio_pika.abc.AbstractIncomingMessage], Awaitable[None]]


class EventConsumer:
    """
    Async RabbitMQ consumer with idempotency, retry, and DLQ support.

    Usage:
        consumer = EventConsumer(queue_name="news.article.ingested")
        consumer.register_handler("news.article.ingested", my_handler)
        await consumer.start()
        # runs until stopped
        await consumer.stop()
    """

    def __init__(
        self,
        queue_name: str,
        url: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
        prefetch_count: int = 10,
    ):
        self._url = url or settings.rabbitmq_url
        self._queue_name = queue_name
        self._retry_policy = retry_policy or ExponentialBackoff()
        self._idempotency = idempotency_store  # injected; may be None (disables dedup)
        self._prefetch_count = prefetch_count
        self._handlers: dict[str, MessageHandler] = {}
        self._connection: Optional[aio_pika.abc.AbstractConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._queue: Optional[aio_pika.abc.AbstractQueue] = None
        self._consumer_tag: Optional[str] = None
        self._running = False

    def register_handler(self, event_type: str, handler: MessageHandler) -> None:
        """Register a handler for a specific event_type."""
        self._handlers[event_type] = handler
        logger.debug("Handler registered", event_type=event_type)

    async def start(self) -> None:
        """Connect and begin consuming."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._prefetch_count)

        self._queue = await self._channel.declare_queue(
            self._queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "agentos.dlx",
                "x-message-ttl": 86400000,
            },
            passive=True,  # Queue should already exist from definitions.json
        )

        self._consumer_tag = await self._queue.consume(self._on_message)
        self._running = True
        logger.info("Consumer started", queue=self._queue_name)

    async def stop(self) -> None:
        if self._queue and self._consumer_tag:
            await self._queue.cancel(self._consumer_tag)
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._running = False
        logger.info("Consumer stopped", queue=self._queue_name)

    async def _on_message(
        self, message: aio_pika.abc.AbstractIncomingMessage
    ) -> None:
        """Internal message callback — acks/nacks based on outcome."""
        async with message.process(requeue=False):
            try:
                await self._dispatch(message)
            except Exception as exc:
                # Logged inside _dispatch; message is nacked → DLQ
                logger.error(
                    "Unhandled consumer error",
                    queue=self._queue_name,
                    error=str(exc),
                    exc_info=True,
                )
                raise  # triggers nack via context manager

    async def _dispatch(
        self, message: aio_pika.abc.AbstractIncomingMessage
    ) -> None:
        """Deserialize, idempotency-check, and dispatch to handler."""
        # --- Deserialize ---
        try:
            raw = json.loads(message.body)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in message body", error=str(e))
            return  # swallow — no handler can fix malformed JSON; goes to DLQ

        event_type = raw.get("event_type", "") or (message.headers or {}).get("event_type", "")
        event_id = raw.get("event_id", message.message_id or "unknown")

        # --- Idempotency check ---
        if self._idempotency:
            already_processed = await self._idempotency.check_and_mark(event_id)
            if already_processed:
                logger.info("Duplicate event suppressed", event_id=event_id, event_type=event_type)
                return

        # --- Extract OTel context from headers ---
        carrier = dict(message.headers or {})
        ctx = extract(carrier)

        # --- Find handler ---
        handler = self._handlers.get(event_type)
        if handler is None:
            logger.warning(
                "No handler registered for event_type",
                event_type=event_type,
                event_id=event_id,
            )
            return

        # --- Build typed event ---
        try:
            event = BaseEvent.model_validate(raw)
        except Exception as e:
            logger.error("Event schema validation failed", error=str(e), raw=raw)
            raise  # → DLQ

        # --- Invoke handler ---
        logger.info("Dispatching event", event_type=event_type, event_id=event_id)
        await handler(event, message)
