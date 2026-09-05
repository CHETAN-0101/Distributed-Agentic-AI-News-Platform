"""
AgentOS — Idempotency store using Redis.

Prevents duplicate event/task execution by tracking event IDs.
"""
from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)

# How long to keep "seen" markers (24 hours by default)
DEFAULT_TTL_SECONDS = 86400
IDEMPOTENCY_KEY_PREFIX = "agentos:idempotency:"


class IdempotencyStore:
    """
    Redis-backed idempotency store.

    check_and_mark(event_id) → True if already seen (duplicate), False if new.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        key_prefix: str = IDEMPOTENCY_KEY_PREFIX,
    ):
        self._redis_url = redis_url or settings.redis_url
        self._ttl = ttl_seconds
        self._prefix = key_prefix
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._client = await aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections,
        )
        logger.info("IdempotencyStore connected")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def check_and_mark(self, event_id: str) -> bool:
        """
        Atomically check and mark an event ID.

        Returns True if event_id was already seen (duplicate → skip).
        Returns False if event_id is new (first time → process).
        """
        if self._client is None:
            raise RuntimeError("IdempotencyStore not connected")

        key = f"{self._prefix}{event_id}"
        # SET key "1" NX EX ttl — returns True only if key was set (first time)
        was_new = await self._client.set(key, "1", nx=True, ex=self._ttl)
        return not bool(was_new)  # True if already existed = duplicate

    async def mark_as_seen(self, event_id: str) -> None:
        """Explicitly mark an event as seen (without checking)."""
        if self._client is None:
            raise RuntimeError("IdempotencyStore not connected")
        key = f"{self._prefix}{event_id}"
        await self._client.set(key, "1", ex=self._ttl)

    async def is_seen(self, event_id: str) -> bool:
        """Check if an event has been seen without marking."""
        if self._client is None:
            raise RuntimeError("IdempotencyStore not connected")
        key = f"{self._prefix}{event_id}"
        return bool(await self._client.exists(key))

    async def delete(self, event_id: str) -> None:
        """Remove an event from the idempotency store (for testing/admin)."""
        if self._client is None:
            raise RuntimeError("IdempotencyStore not connected")
        key = f"{self._prefix}{event_id}"
        await self._client.delete(key)
