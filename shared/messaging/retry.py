"""
AgentOS — Retry policies with exponential backoff.

Used by both the messaging consumer and the workflow engine.
"""
from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Optional

from shared.logging import get_logger

logger = get_logger(__name__)


class RetryPolicy(ABC):
    """Abstract base class for retry policies."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Return wait time in seconds before attempt N."""
        ...

    @abstractmethod
    def should_retry(self, attempt: int, max_retries: int) -> bool:
        """Return True if another attempt should be made."""
        ...


class ExponentialBackoff(RetryPolicy):
    """
    Exponential backoff with optional jitter.

    Attempt 1 → base_delay
    Attempt 2 → base_delay * multiplier
    Attempt 3 → base_delay * multiplier^2
    ...capped at max_delay.

    Example schedule (base=2, mult=2.5, max=60):
        0 → 2s
        1 → 5s
        2 → 12.5s
        3 → 31.25s
        4 → 60s (capped)
    """

    def __init__(
        self,
        base_delay: float = 2.0,
        multiplier: float = 2.5,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self._base = base_delay
        self._mult = multiplier
        self._max = max_delay
        self._jitter = jitter

    def get_delay(self, attempt: int) -> float:
        delay = min(self._base * (self._mult ** attempt), self._max)
        if self._jitter:
            delay *= (0.5 + random.random() * 0.5)  # ±50% jitter
        return delay

    def should_retry(self, attempt: int, max_retries: int) -> bool:
        return attempt < max_retries


class FixedDelay(RetryPolicy):
    """Fixed delay between retries."""

    def __init__(self, delay: float = 5.0):
        self._delay = delay

    def get_delay(self, attempt: int) -> float:
        return self._delay

    def should_retry(self, attempt: int, max_retries: int) -> bool:
        return attempt < max_retries


async def retry_with_policy(
    coro_factory,
    policy: RetryPolicy,
    max_retries: int = 3,
    task_id: Optional[str] = None,
    capability: Optional[str] = None,
):
    """
    Execute an async coroutine factory with a retry policy.

    Args:
        coro_factory: Callable that returns a coroutine (called on each attempt).
        policy:       RetryPolicy instance.
        max_retries:  Maximum number of attempts (total = max_retries + 1).
        task_id:      For logging context.
        capability:   For logging context.

    Returns:
        The result of the coroutine on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    attempt = 0
    last_exc: Optional[Exception] = None

    while policy.should_retry(attempt, max_retries) or attempt == 0:
        try:
            if attempt > 0:
                delay = policy.get_delay(attempt - 1)
                logger.info(
                    "Retrying after delay",
                    attempt=attempt,
                    delay_s=round(delay, 2),
                    task_id=task_id,
                    capability=capability,
                )
                await asyncio.sleep(delay)

            result = await coro_factory()
            if attempt > 0:
                logger.info("Retry succeeded", attempt=attempt, task_id=task_id)
            return result

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Attempt failed",
                attempt=attempt,
                error=str(exc),
                task_id=task_id,
                capability=capability,
            )
            attempt += 1

    logger.error(
        "All retries exhausted",
        max_retries=max_retries,
        task_id=task_id,
        capability=capability,
        last_error=str(last_exc),
    )
    raise last_exc  # type: ignore[misc]
