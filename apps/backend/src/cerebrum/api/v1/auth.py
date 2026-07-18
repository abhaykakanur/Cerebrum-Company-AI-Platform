"""The authentication API surface: login, refresh, logout, and the
current-user endpoint — CIS Phase 1 Prompt 5's Login/Refresh/Logout/Current
User Dependency deliverables surfaced over HTTP.

Routing only — no business/security logic lives here; every route
delegates to :mod:`cerebrum.application.auth`, per this codebase's
established api/ layer responsibility ("HTTP layer only. Never contains
business logic.").
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.schemas.auth import (
    CurrentUserResponse,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from cerebrum.application.auth.dtos import TokenPair
from cerebrum.dependencies.auth import (
    AuthenticationServiceDep,
    CurrentUserDep,
    LoginRateLimitDep,
)
from cerebrum.middleware.context import get_client_ip

router = APIRouter(
    prefix="/auth", tags=["Authentication"], responses=STANDARD_ERROR_RESPONSES
)


def _to_token_response(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    authentication_service: AuthenticationServiceDep,
    _rate_limit: LoginRateLimitDep,
) -> TokenResponse:
    """OAuth2 Password Flow: ``form.username`` carries the email address
    (OAuth2's form field is named ``username`` regardless of what the
    identifier actually is — see the spec). Rate-limited per client IP —
    see cerebrum.dependencies.auth.enforce_login_rate_limit.
    """
    token_pair = await authentication_service.login(
        email=form.username,
        password=form.password,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return _to_token_response(token_pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    body: RefreshRequest,
    authentication_service: AuthenticationServiceDep,
) -> TokenResponse:
    """Token Rotation: the presented refresh token is revoked and a new
    pair is issued — see
    cerebrum.application.auth.authentication_service.AuthenticationService.refresh.
    """
    token_pair = await authentication_service.refresh(
        refresh_token=body.refresh_token,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return _to_token_response(token_pair)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    body: LogoutRequest,
    authentication_service: AuthenticationServiceDep,
) -> None:
    """Idempotent — see
    cerebrum.application.auth.authentication_service.AuthenticationService.logout.
    """
    await authentication_service.logout(
        refresh_token=body.refresh_token, ip_address=get_client_ip(request)
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: CurrentUserDep) -> CurrentUserResponse:
    """The Current User Dependency, surfaced over HTTP."""
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
    )
