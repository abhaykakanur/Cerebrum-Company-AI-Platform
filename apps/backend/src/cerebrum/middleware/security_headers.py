"""Security response headers: one middleware, one responsibility — no
business rules, no database access, per CIS Phase 1 Prompt 3 Section 3's
Middleware Principles.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from cerebrum.config.environment import Environment

_STATIC_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attaches standard security headers to every response.
    ``Strict-Transport-Security`` is added only in production-like
    environments, since it is unsafe to send over plain HTTP local
    development traffic.
    """

    def __init__(self, app: ASGIApp, *, environment: Environment) -> None:
        super().__init__(app)
        self._environment = environment

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in _STATIC_HEADERS.items():
            response.headers[name] = value
        if self._environment.is_production_like:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response
