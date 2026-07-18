"""Authentication middleware: resolves *who*, if anyone, is making the
request from its ``Authorization: Bearer <token>`` header, and attaches
the result to ``request.state.auth_identity`` for
cerebrum.middleware.request_context.RequestContextMiddleware (which runs
immediately after this middleware — see cerebrum.middleware.registry) to
fold into the request's :class:`~cerebrum.middleware.context.RequestContext`.

This middleware answers "who is this?", never "is this allowed?" — no
request is rejected here for lacking a token; a route that requires
authentication rejects it via
cerebrum.dependencies.auth.get_current_user, per CIS Phase 1 Prompt 5's
"Anonymous requests where allowed" requirement. A *presented* token that
is invalid or expired, however, is rejected immediately: the caller
attempted authentication and it failed, which is different from not
attempting it at all, and every route benefits from that failing loudly
and consistently rather than silently degrading to "anonymous."

Exceptions raised inside ``BaseHTTPMiddleware.dispatch()`` bypass
FastAPI's ``@app.exception_handler``-registered handlers entirely —
verified empirically; Starlette's ``ExceptionMiddleware`` sits *inside*
every user-added middleware in the ASGI stack, not outside it (see
cerebrum.middleware.registry's docstring for the same
reversed-registration-order subtlety). This middleware therefore never
raises a caught exception — it calls
cerebrum.core.exception_handlers.handle_platform_exception directly to
build the same standardized error envelope every other exception path
produces, and returns that response itself.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from cerebrum.infrastructure.security.jwt import TokenService, TokenType
from cerebrum.middleware.context import AuthIdentity
from cerebrum.shared.errors.base import PlatformException

_BEARER_SCHEME = "bearer"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, token_service: TokenService) -> None:
        super().__init__(app)
        self._tokens = token_service

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.auth_identity = None

        token = self._extract_bearer_token(request)
        if token is not None:
            try:
                payload = self._tokens.decode_token(
                    token, expected_type=TokenType.ACCESS
                )
            except PlatformException as exc:
                # See this module's docstring: importing the handler
                # lazily avoids a module-level import cycle between
                # core/ (which imports middleware/ to register it) and
                # middleware/ (which would otherwise import core/ at
                # import time rather than call time).
                from cerebrum.core.exception_handlers import handle_platform_exception

                return await handle_platform_exception(request, exc)

            request.state.auth_identity = AuthIdentity(
                user_id=payload.subject, organization_id=payload.organization_id
            )

        return await call_next(request)

    @staticmethod
    def _extract_bearer_token(request: Request) -> str | None:
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != _BEARER_SCHEME or not token:
            return None
        return token
