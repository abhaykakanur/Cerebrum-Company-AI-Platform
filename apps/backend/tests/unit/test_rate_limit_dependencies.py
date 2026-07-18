"""Proves CIS Phase 1 Prompt 6's completed Rate Limiting Framework: the
Per User/Per Tenant/Per API Key/Anonymous dependency factories in
cerebrum.dependencies.rate_limit correctly key and enforce independent
limits, and fail open when Redis is unreachable — mirroring
test_rate_limiter.py's fake-Redis approach (see that module's docstring
for why a real Redis connection is deliberately avoided in this suite).
Called directly with hand-built fake dependencies rather than over HTTP:
these are dependency *factories*, and their returned closures' parameter
names match FastAPI's own dependency names exactly, so invoking them
directly is calling the same code path FastAPI would.
"""

import uuid
from types import SimpleNamespace

import pytest

from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.rate_limit import (
    rate_limit_anonymous,
    rate_limit_per_api_key,
    rate_limit_per_tenant,
    rate_limit_per_user,
)
from cerebrum.middleware.context import AuthIdentity
from cerebrum.shared.errors.exceptions import RateLimitExceededException

pytestmark = pytest.mark.unit


class _FakeRedis:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None

    async def ttl(self, key: str) -> int:
        return 60


def _state(*, connected: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        redis=SimpleNamespace(is_connected=connected, client=_FakeRedis())
    )


def _settings(*, max_attempts: int = 2, window_seconds: int = 60) -> SimpleNamespace:
    return SimpleNamespace(
        security=SecuritySettings(
            api_rate_limit_requests=max_attempts,
            api_rate_limit_window_seconds=window_seconds,
        )
    )


async def test_per_user_blocks_after_the_threshold() -> None:
    identity = AuthIdentity(user_id=uuid.uuid4(), organization_id=uuid.uuid4())
    state, settings = _state(), _settings(max_attempts=2)
    check = rate_limit_per_user()

    await check(identity=identity, state=state, settings=settings)
    await check(identity=identity, state=state, settings=settings)
    with pytest.raises(RateLimitExceededException):
        await check(identity=identity, state=state, settings=settings)


async def test_per_user_limits_are_independent_per_user() -> None:
    state, settings = _state(), _settings(max_attempts=1)
    check = rate_limit_per_user()
    alice = AuthIdentity(user_id=uuid.uuid4(), organization_id=uuid.uuid4())
    bob = AuthIdentity(user_id=uuid.uuid4(), organization_id=uuid.uuid4())

    await check(identity=alice, state=state, settings=settings)
    await check(identity=bob, state=state, settings=settings)  # must not raise


async def test_per_tenant_shares_one_counter_across_users_in_the_same_org() -> None:
    tenant_id = uuid.uuid4()
    state, settings = _state(), _settings(max_attempts=1)
    check = rate_limit_per_tenant()

    await check(tenant_id=tenant_id, state=state, settings=settings)
    with pytest.raises(RateLimitExceededException):
        await check(tenant_id=tenant_id, state=state, settings=settings)


async def test_per_api_key_keys_by_hash_not_raw_key() -> None:
    state, settings = _state(), _settings(max_attempts=1)
    check = rate_limit_per_api_key()
    request = SimpleNamespace(headers={"X-API-Key": "ck_secret"})

    await check(request=request, state=state, settings=settings)
    with pytest.raises(RateLimitExceededException):
        await check(request=request, state=state, settings=settings)


async def test_per_api_key_is_a_noop_without_the_header() -> None:
    state, settings = _state(), _settings(max_attempts=1)
    check = rate_limit_per_api_key()
    request = SimpleNamespace(headers={})

    await check(request=request, state=state, settings=settings)  # must not raise


async def test_anonymous_keys_by_client_ip() -> None:
    state, settings = _state(), _settings(max_attempts=1)
    check = rate_limit_anonymous()
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="203.0.113.5"))

    await check(request=request, state=state, settings=settings)
    with pytest.raises(RateLimitExceededException):
        await check(request=request, state=state, settings=settings)


async def test_fails_open_when_redis_is_disconnected() -> None:
    identity = AuthIdentity(user_id=uuid.uuid4(), organization_id=uuid.uuid4())
    state, settings = _state(connected=False), _settings(max_attempts=1)
    check = rate_limit_per_user()

    await check(identity=identity, state=state, settings=settings)  # must not raise


async def test_factory_override_takes_precedence_over_settings_default() -> None:
    identity = AuthIdentity(user_id=uuid.uuid4(), organization_id=uuid.uuid4())
    state, settings = _state(), _settings(max_attempts=1000)
    check = rate_limit_per_user(max_attempts=1, window_seconds=60)

    await check(identity=identity, state=state, settings=settings)
    with pytest.raises(RateLimitExceededException):
        await check(identity=identity, state=state, settings=settings)
