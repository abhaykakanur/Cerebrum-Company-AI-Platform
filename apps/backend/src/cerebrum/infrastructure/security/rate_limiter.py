"""Redis-backed rate limiting foundation (CIS Phase 1 Prompt 5). A fixed
window counter — simple, and sufficient for a foundation: one ``INCR``
plus one ``EXPIRE`` on the window's first hit, reusing the
already-connected :class:`~cerebrum.infrastructure.cache.manager.RedisClientManager`'s
client rather than a new connection.

Applied to the login endpoint only at this milestone (see
cerebrum.api.v1.auth) — "foundation," not a blanket rate limiter over
every route; a future phase decides which other endpoints need it.
"""

from redis.asyncio import Redis

from cerebrum.shared.errors.exceptions import RateLimitExceededException

_KEY_PREFIX = "cerebrum:rate_limit"


class RateLimiter:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def check(self, key: str, *, max_attempts: int, window_seconds: int) -> None:
        """Raises :class:`~cerebrum.shared.errors.exceptions.RateLimitExceededException`
        once ``key`` has been checked more than ``max_attempts`` times
        within ``window_seconds``. Every call counts as an attempt,
        including ones that are themselves rejected — a caller hammering
        past their limit doesn't get free, uncounted retries.
        """
        full_key = f"{_KEY_PREFIX}:{key}"
        current = await self._redis.incr(full_key)
        if current == 1:
            await self._redis.expire(full_key, window_seconds)

        if current > max_attempts:
            ttl = await self._redis.ttl(full_key)
            raise RateLimitExceededException(
                "Too many attempts. Please wait before trying again.",
                retry_after_seconds=max(ttl, 1),
                context={"key": key, "max_attempts": max_attempts},
            )
