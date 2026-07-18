"""General-purpose Rate Limiting dependencies (CIS Phase 1 Prompt 6),
completing the Rate Limiting Foundation CIS Phase 1 Prompt 5 built for
the login endpoint specifically. Four of
docs/architecture/specification/81_API_Standards.md's five Rate Limiting
dimensions are covered here — Per User, Per Tenant (Organization), Per
API Key, Per IP (Anonymous); Per Workspace is Deferred to the first
workspace-scoped route that needs it, following the same
build-what's-needed discipline as
cerebrum.repositories.postgres.role_repository's docstring.

Each dimension is a dependency *factory* — ``Depends(rate_limit_per_user())``
— mirroring cerebrum.dependencies.auth.require_permission's shape, so a
route can override the default threshold
(``SecuritySettings.api_rate_limit_requests``/``api_rate_limit_window_seconds``)
without a new function. Every dimension fails open (logs a warning,
allows the request) when Redis is unreachable — see
cerebrum.dependencies.auth.enforce_login_rate_limit's identical
rationale: rate limiting is defense-in-depth, and no route's basic
availability should become conditional on a cache being up.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request

from cerebrum.core.logging import get_logger
from cerebrum.core.state import ApplicationState
from cerebrum.dependencies.auth import CurrentIdentityDep
from cerebrum.dependencies.request_context import TenantIdDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.dependencies.state import ApplicationStateDep
from cerebrum.infrastructure.security.hashing import hash_secret
from cerebrum.infrastructure.security.rate_limiter import RateLimiter
from cerebrum.middleware.context import get_client_ip

_logger = get_logger("cerebrum.dependencies.rate_limit")


async def _enforce(
    *,
    state: ApplicationState,
    settings_max_attempts: int,
    settings_window_seconds: int,
    key: str,
    max_attempts: int | None,
    window_seconds: int | None,
) -> None:
    if not state.redis.is_connected:
        _logger.warning("rate_limit.unavailable", reason="Redis is not connected.")
        return
    limiter = RateLimiter(state.redis.client)
    await limiter.check(
        key,
        max_attempts=max_attempts or settings_max_attempts,
        window_seconds=window_seconds or settings_window_seconds,
    )


def rate_limit_per_user(
    *, max_attempts: int | None = None, window_seconds: int | None = None
) -> Callable[..., Awaitable[None]]:
    """Rate Limiting's Per User dimension. Requires authentication — see
    :data:`~cerebrum.dependencies.auth.CurrentIdentityDep`.
    """

    async def _check(
        identity: CurrentIdentityDep, state: ApplicationStateDep, settings: SettingsDep
    ) -> None:
        await _enforce(
            state=state,
            settings_max_attempts=settings.security.api_rate_limit_requests,
            settings_window_seconds=settings.security.api_rate_limit_window_seconds,
            key=f"user:{identity.user_id}",
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )

    return _check


def rate_limit_per_tenant(
    *, max_attempts: int | None = None, window_seconds: int | None = None
) -> Callable[..., Awaitable[None]]:
    """Rate Limiting's Per Tenant (Organization) dimension — every user in
    the same organization shares one counter, unlike
    :func:`rate_limit_per_user`.
    """

    async def _check(
        tenant_id: TenantIdDep, state: ApplicationStateDep, settings: SettingsDep
    ) -> None:
        await _enforce(
            state=state,
            settings_max_attempts=settings.security.api_rate_limit_requests,
            settings_window_seconds=settings.security.api_rate_limit_window_seconds,
            key=f"tenant:{tenant_id}",
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )

    return _check


def rate_limit_per_api_key(
    *, max_attempts: int | None = None, window_seconds: int | None = None
) -> Callable[..., Awaitable[None]]:
    """Rate Limiting's Per API Key dimension — keyed by the presented
    ``X-API-Key`` header's hash (never the raw key — see
    cerebrum.infrastructure.security.hashing), independent of whether the
    key is ultimately valid; a route depending on this alongside API key
    validation (cerebrum.application.auth.api_key_service.APIKeyService.validate)
    limits by the *claimed* key up front. No-ops (no limit is applied) if
    the header is absent — a route mixing authentication methods only
    rate-limits the calls that actually present a key.
    """

    async def _check(
        request: Request, state: ApplicationStateDep, settings: SettingsDep
    ) -> None:
        raw_key = request.headers.get("X-API-Key")
        if raw_key is None:
            return
        await _enforce(
            state=state,
            settings_max_attempts=settings.security.api_rate_limit_requests,
            settings_window_seconds=settings.security.api_rate_limit_window_seconds,
            key=f"api_key:{hash_secret(raw_key)}",
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )

    return _check


def rate_limit_anonymous(
    *, max_attempts: int | None = None, window_seconds: int | None = None
) -> Callable[..., Awaitable[None]]:
    """Rate Limiting's Per IP dimension — the fallback for a caller with
    no identity at all, keyed by client IP (Trusted Proxy Support
    already resolves the real IP behind a configured reverse proxy — see
    cerebrum.middleware.request_context).
    """

    async def _check(
        request: Request, state: ApplicationStateDep, settings: SettingsDep
    ) -> None:
        await _enforce(
            state=state,
            settings_max_attempts=settings.security.api_rate_limit_requests,
            settings_window_seconds=settings.security.api_rate_limit_window_seconds,
            key=f"anonymous:{get_client_ip(request) or 'unknown'}",
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )

    return _check
