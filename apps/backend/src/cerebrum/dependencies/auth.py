"""Identity & Security dependency providers (CIS Phase 1 Prompt 5):
current-identity/current-user resolution, RBAC route protection, and the
application services routes need — assembled per request from the
already-established :data:`~cerebrum.dependencies.database.DbSessionDep`
and :data:`~cerebrum.dependencies.settings.SettingsDep`, following the
exact pattern documented in docs/architecture/dependency-injection.md.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from cerebrum.application.auth.api_key_service import APIKeyService
from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.auth.authentication_service import AuthenticationService
from cerebrum.application.auth.authorization_service import AuthorizationService
from cerebrum.core.logging import get_logger
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.dependencies.state import ApplicationStateDep
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.security.jwt import TokenService
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.infrastructure.security.rate_limiter import RateLimiter
from cerebrum.middleware.context import (
    AuthIdentity,
    get_client_ip,
    get_current_request_context,
)
from cerebrum.repositories.postgres.api_key_repository import APIKeyRepository
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.role_repository import RoleRepository
from cerebrum.repositories.postgres.session_repository import UserSessionRepository
from cerebrum.repositories.postgres.user_repository import UserRepository
from cerebrum.shared.errors.exceptions import (
    AuthenticationException,
    ValidationException,
)

_logger = get_logger("cerebrum.dependencies.auth")

# ``auto_error=False``: presence/absence of a token is enforced by
# get_current_identity below (with a consistent AuthenticationException,
# not FastAPI's own generic 401), not by this scheme itself. Declaring it
# is still what makes FastAPI emit the correct OAuth2 security scheme in
# the generated OpenAPI document (tokenUrl points at the real login
# endpoint), giving Swagger UI's "Authorize" button something to work
# against — see cerebrum.core.openapi.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
    description="Bearer access token from `POST /api/v1/auth/login` or "
    "`/api/v1/auth/refresh`. Pass as `Authorization: Bearer <access_token>`.",
)


# --- Infrastructure primitives (Singleton — cheap, stateless construction) --


def get_token_service(settings: SettingsDep) -> TokenService:
    return TokenService(settings.security)


def get_password_hasher(settings: SettingsDep) -> PasswordHasher:
    return PasswordHasher(settings.security)


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]


async def enforce_login_rate_limit(
    request: Request, state: ApplicationStateDep, settings: SettingsDep
) -> None:
    """Rate Limiting Foundation, applied to the login endpoint (see
    cerebrum.api.v1.auth). Fails open — logging a warning rather than
    blocking every login — if Redis is unreachable: rate limiting is
    defense-in-depth, and "Users can authenticate" must not become
    conditional on a cache being up, per
    cerebrum.core.lifecycle's graceful-degradation design (CIS Phase 1
    Prompt 4).
    """
    if not state.redis.is_connected:
        _logger.warning("rate_limit.unavailable", reason="Redis is not connected.")
        return

    client_ip = get_client_ip(request) or "unknown"
    limiter = RateLimiter(state.redis.client)
    await limiter.check(
        f"login:{client_ip}",
        max_attempts=settings.security.login_rate_limit_attempts,
        window_seconds=settings.security.login_rate_limit_window_seconds,
    )


LoginRateLimitDep = Annotated[None, Depends(enforce_login_rate_limit)]


# --- Identity resolution (Scoped — per request) ------------------------------


def get_current_identity(
    request: Request, _token: Annotated[str | None, Depends(oauth2_scheme)]
) -> AuthIdentity:
    """Requires authentication: raises
    :class:`~cerebrum.shared.errors.exceptions.AuthenticationException`
    if no valid access token was presented. The identity itself was
    already resolved by cerebrum.middleware.authentication.AuthenticationMiddleware
    — this dependency only reads ``request.state.auth_identity``, never
    re-decodes the token.
    """
    identity: AuthIdentity | None = getattr(request.state, "auth_identity", None)
    if identity is None:
        raise AuthenticationException("Not authenticated.")
    return identity


def get_optional_current_identity(
    request: Request, _token: Annotated[str | None, Depends(oauth2_scheme)]
) -> AuthIdentity | None:
    """For a route where CIS Phase 1 Prompt 5's "Anonymous requests
    where allowed" applies — returns ``None`` rather than raising.
    """
    return getattr(request.state, "auth_identity", None)


CurrentIdentityDep = Annotated[AuthIdentity, Depends(get_current_identity)]
OptionalIdentityDep = Annotated[
    AuthIdentity | None, Depends(get_optional_current_identity)
]


async def get_current_user(identity: CurrentIdentityDep, session: DbSessionDep) -> User:
    """The "Current User Dependency" CIS Phase 1 Prompt 5 asks for —
    loads the full :class:`~cerebrum.infrastructure.database.models.user.User`
    row, unlike :data:`CurrentIdentityDep`, which only carries the IDs
    already embedded in the access token.
    """
    user = await UserRepository(session).get_by_id(identity.user_id)
    if user is None or not user.is_active:
        raise AuthenticationException("Account is no longer active.")
    return user


async def get_optional_current_user(
    identity: OptionalIdentityDep, session: DbSessionDep
) -> User | None:
    if identity is None:
        return None
    user = await UserRepository(session).get_by_id(identity.user_id)
    if user is None or not user.is_active:
        return None
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
OptionalCurrentUserDep = Annotated[User | None, Depends(get_optional_current_user)]


# --- Multi-tenancy: workspace context (Scoped) -------------------------------


def get_current_workspace_id() -> uuid.UUID:
    """Reads ``workspace_id`` off the already-bound
    :class:`~cerebrum.middleware.context.RequestContext` (populated from
    the ``X-Workspace-ID`` header — see
    cerebrum.middleware.request_context) and parses it. Raises
    :class:`~cerebrum.shared.errors.exceptions.ValidationException` if
    the header is absent or malformed — a route depending on this
    requires workspace scoping to proceed at all.
    """
    context = get_current_request_context()
    if context is None or context.workspace_id is None:
        raise ValidationException("X-Workspace-ID header is required for this request.")
    try:
        return uuid.UUID(context.workspace_id)
    except ValueError as exc:
        raise ValidationException("X-Workspace-ID header is not a valid UUID.") from exc


WorkspaceIdDep = Annotated[uuid.UUID, Depends(get_current_workspace_id)]


# --- RBAC route protection ---------------------------------------------------


def get_authorization_service(session: DbSessionDep) -> AuthorizationService:
    return AuthorizationService(
        role_repository=RoleRepository(session),
        audit_service=AuditService(AuditEventRepository(session)),
    )


AuthorizationServiceDep = Annotated[
    AuthorizationService, Depends(get_authorization_service)
]


def require_permission(permission_code: str) -> Callable[..., Awaitable[None]]:
    """Route protection: ``Depends(require_permission("workspace:read"))``.
    A dependency *factory*, not a dependency itself — each call returns a
    fresh closure bound to ``permission_code``, since FastAPI dependencies
    are plain callables and this is the standard way to parameterize one.
    """

    async def _check(
        identity: CurrentIdentityDep,
        workspace_id: WorkspaceIdDep,
        authorization_service: AuthorizationServiceDep,
    ) -> None:
        await authorization_service.require_permission(
            user_id=identity.user_id,
            workspace_id=workspace_id,
            permission_code=permission_code,
        )

    return _check


# --- Application services (Scoped) -------------------------------------------


def get_authentication_service(
    session: DbSessionDep,
    settings: SettingsDep,
    token_service: TokenServiceDep,
    password_hasher: PasswordHasherDep,
) -> AuthenticationService:
    return AuthenticationService(
        user_repository=UserRepository(session),
        session_repository=UserSessionRepository(session),
        password_hasher=password_hasher,
        token_service=token_service,
        audit_service=AuditService(AuditEventRepository(session)),
        settings=settings.security,
    )


AuthenticationServiceDep = Annotated[
    AuthenticationService, Depends(get_authentication_service)
]


def get_api_key_service(session: DbSessionDep, settings: SettingsDep) -> APIKeyService:
    return APIKeyService(
        api_key_repository=APIKeyRepository(session), settings=settings.security
    )


APIKeyServiceDep = Annotated[APIKeyService, Depends(get_api_key_service)]
