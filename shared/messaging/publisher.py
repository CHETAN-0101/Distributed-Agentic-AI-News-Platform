"""
AgentOS — RabbitMQ event publisher.

Features:
- Durable topic exchanges
- Persistent messages
- OpenTelemetry header propagation
- Correlation IDs
- JSON serialization with datetime support
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import aio_pika
import aio_pika.abc

try:
    from opentelemetry import trace
    from opentelemetry.propagate import inject
except ImportError:
    trace = None  # type: ignore[assignment]
    def inject(carrier: Any) -> None:  # type: ignore[misc]
        pass

from shared.config import settings
from shared.logging import get_logger
from shared.schemas.events import BaseEvent

logger = get_logger(__name__)

# Exchange → routing key prefix map
EXCHANGE_MAP: dict[str, str] = {
    "task.": "agentos.tasks",
    "agent.": "agentos.agents",
    "workflow.": "agentos.workflows",
    "news.": "agentos.news",
    "evidence.": "agentos.evidence",
    "human.": "agentos.human",
}

DEFAULT_EXCHANGE = "agentos.tasks"


def _get_exchange_name(routing_key: str) -> str:
    for prefix, exchange in EXCHANGE_MAP.items():
        if routing_key.startswith(prefix):
            return exchange
    return DEFAULT_EXCHANGE


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class EventPublisher:
    """
    Async RabbitMQ publisher.

    Usage:
        publisher = EventPublisher()
        await publisher.connect()
        await publisher.publish(event)
        await publisher.close()

    Or use as async context manager:
        async with EventPublisher() as pub:
            await pub.publish(event)
    """

    def __init__(self, url: Optional[str] = None):
        self._url = url or settings.rabbitmq_url
        self._connection: Optional[aio_pika.abc.AbstractConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchanges: dict[str, aio_pika.abc.AbstractExchange] = {}

    async def connect(self) -> None:
        """Open connection and channel, declare exchanges."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()

        # Declare all exchanges (idempotent)
        for exchange_name in set(EXCHANGE_MAP.values()):
            exchange = await self._channel.declare_exchange(
                exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            self._exchanges[exchange_name] = exchange

        logger.info("EventPublisher connected", url=self._url)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def __aenter__(self) -> "EventPublisher":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def publish(
        self,
        event: BaseEvent,
        priority: int = 0,
    ) -> None:
        """
        Publish a typed event to the appropriate exchange.

        Args:
            event:    The event to publish (must subclass BaseEvent).
            priority: Message priority (0–9).
        """
        if self._channel is None:
            raise RuntimeError("EventPublisher not connected. Call connect() first.")

        routing_key = event.event_type
        exchange_name = _get_exchange_name(routing_key)
        exchange = self._exchanges.get(exchange_name)

        if exchange is None:
            raise RuntimeError(f"Exchange '{exchange_name}' not found. Was connect() called?")

        # Build headers — inject OTel trace context for distributed tracing
        headers: dict[str, str] = {
            "event_type": event.event_type,
            "event_version": event.event_version,
            "tenant_id": event.tenant_id,
            "correlation_id": event.correlation_id or str(uuid4()),
        }
        if event.trace_id:
            headers["trace_id"] = event.trace_id
        inject(headers)  # Injects W3C/B3 trace headers

        body = json.dumps(event.model_dump(), default=_json_default).encode()

        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            message_id=event.event_id,
            correlation_id=event.correlation_id or headers["correlation_id"],
            headers=headers,
            priority=priority,
        )

        await exchange.publish(message, routing_key=routing_key)

        logger.debug(
            "Event published",
            event_type=event.event_type,
            event_id=event.event_id,
            routing_key=routing_key,
            exchange=exchange_name,
            tenant_id=event.tenant_id,
        )

    async def publish_raw(
        self,
        routing_key: str,
        payload: dict[str, Any],
        tenant_id: str = "default",
        correlation_id: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        """
        Publish a raw dict payload, wrapping it in a BaseEvent envelope.
        Returns the generated event_id.
        """
        event = BaseEvent(
            event_type=routing_key,
            tenant_id=tenant_id,
            correlation_id=correlation_id or str(uuid4()),
            payload=payload,
        )
        await self.publish(event, priority=priority)
        return event.event_id
