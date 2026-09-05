"""Unit tests for AgentOS Messaging, Retry Policies, and Idempotency."""
import pytest
import asyncio
from shared.messaging.retry import ExponentialBackoff, FixedDelay, retry_with_policy
from shared.messaging.idempotency import InMemoryIdempotencyStore


@pytest.mark.asyncio
async def test_in_memory_idempotency():
    store = InMemoryIdempotencyStore()

    # First check: not duplicate (returns False)
    is_duplicate = await store.check_and_mark("msg-uuid-001")
    assert is_duplicate is False

    # Second check: is duplicate (returns True)
    is_duplicate_again = await store.check_and_mark("msg-uuid-001")
    assert is_duplicate_again is True

    # is_seen check
    assert await store.is_seen("msg-uuid-001") is True
    assert await store.is_seen("msg-uuid-999") is False

    # delete
    await store.delete("msg-uuid-001")
    assert await store.is_seen("msg-uuid-001") is False


def test_fixed_delay_policy():
    policy = FixedDelay(delay=3.0)
    assert policy.get_delay(0) == 3.0
    assert policy.get_delay(5) == 3.0
    assert policy.should_retry(attempt=1, max_retries=3) is True
    assert policy.should_retry(attempt=3, max_retries=3) is False


def test_exponential_backoff_policy():
    policy = ExponentialBackoff(base_delay=1.0, multiplier=2.0, max_delay=10.0, jitter=False)
    assert policy.get_delay(0) == 1.0
    assert policy.get_delay(1) == 2.0
    assert policy.get_delay(2) == 4.0
    assert policy.get_delay(3) == 8.0
    assert policy.get_delay(4) == 10.0  # Capped at max_delay


@pytest.mark.asyncio
async def test_retry_with_policy_success():
    attempts = 0

    async def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Temporary failure")
        return "success"

    policy = FixedDelay(delay=0.01)
    res = await retry_with_policy(flaky_operation, policy=policy, max_retries=3)
    assert res == "success"
    assert attempts == 2


@pytest.mark.asyncio
async def test_retry_with_policy_exhausted():
    async def always_failing():
        raise RuntimeError("Persistent network error")

    policy = FixedDelay(delay=0.01)
    with pytest.raises(RuntimeError, match="Persistent network error"):
        await retry_with_policy(always_failing, policy=policy, max_retries=2)
