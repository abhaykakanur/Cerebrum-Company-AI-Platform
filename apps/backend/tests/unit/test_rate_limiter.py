"""Proves the "Rate limiting foundation" deliverable from CIS Phase 1
Prompt 5.

Uses a minimal in-memory fake standing in for ``redis.asyncio.Redis``
(only ``incr``/``expire``/``ttl``, the three calls
:class:`~cerebrum.infrastructure.security.rate_limiter.RateLimiter`
makes) rather than a real Redis connection — deterministic, and
independent of whether this machine happens to have Redis reachable
(see apps/backend/tests/conftest.py's ``settings`` fixture docstring for
why the ambient environment's Redis, if any, is deliberately avoided
elsewhere in this suite too).
"""

import pytest

from cerebrum.infrastructure.security.rate_limiter import RateLimiter
from cerebrum.shared.errors.exceptions import RateLimitExceededException

pytestmark = pytest.mark.unit


class _FakeRedis:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self._ttls[key] = seconds

    async def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)


async def test_allows_requests_under_the_limit() -> None:
    limiter = RateLimiter(_FakeRedis())  # type: ignore[arg-type]

    for _ in range(5):
        await limiter.check(
            "test-key", max_attempts=5, window_seconds=60
        )  # must not raise


async def test_raises_once_the_limit_is_exceeded() -> None:
    limiter = RateLimiter(_FakeRedis())  # type: ignore[arg-type]

    for _ in range(5):
        await limiter.check("test-key", max_attempts=5, window_seconds=60)

    with pytest.raises(RateLimitExceededException):
        await limiter.check("test-key", max_attempts=5, window_seconds=60)


async def test_exception_carries_a_retry_after_value() -> None:
    limiter = RateLimiter(_FakeRedis())  # type: ignore[arg-type]
    for _ in range(2):
        await limiter.check("test-key", max_attempts=2, window_seconds=120)

    with pytest.raises(RateLimitExceededException) as exc_info:
        await limiter.check("test-key", max_attempts=2, window_seconds=120)
    assert exc_info.value.retry_after_seconds == 120


async def test_different_keys_are_independent() -> None:
    limiter = RateLimiter(_FakeRedis())  # type: ignore[arg-type]

    for _ in range(5):
        await limiter.check("key-a", max_attempts=5, window_seconds=60)

    await limiter.check(
        "key-b", max_attempts=5, window_seconds=60
    )  # must not raise — separate key


async def test_rejected_attempts_still_count() -> None:
    """A caller hammering past their limit doesn't get free, uncounted
    retries — see cerebrum.infrastructure.security.rate_limiter.RateLimiter.check's
    docstring.
    """
    limiter = RateLimiter(_FakeRedis())  # type: ignore[arg-type]
    for _ in range(2):
        await limiter.check("test-key", max_attempts=2, window_seconds=60)
    with pytest.raises(RateLimitExceededException) as first:
        await limiter.check("test-key", max_attempts=2, window_seconds=60)
    with pytest.raises(RateLimitExceededException) as second:
        await limiter.check("test-key", max_attempts=2, window_seconds=60)
    assert second.value.context["key"] == first.value.context["key"]
