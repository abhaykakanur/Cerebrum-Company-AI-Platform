"""Security response headers: one middleware, one responsibility — no
business rules, no database access, per CIS Phase 1 Prompt 3 Section 3's
Middleware Principles.

CIS Phase 1 Prompt 5's "Security headers refinement" extends this
existing middleware rather than adding a second one: a Content-Security-Policy
(scoped away from the interactive OpenAPI docs, which load their assets
from a CDN and would break under a strict CSP), two Cross-Origin-*
isolation headers, and a ``Cache-Control: no-store`` on every response
under the auth API surface, so a token-bearing login/refresh response is
never cached by an intermediary or the browser.
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
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# The interactive docs (see cerebrum.core.metadata) load Swagger
# UI/ReDoc's own JS/CSS from a CDN — a strict CSP would break them, so
# they're excluded rather than the CSP loosened for everyone else.
_DOCS_PATH_SUFFIXES = ("/docs", "/redoc", "/openapi.json")
_AUTH_PATH_PREFIX = "/api/v1/auth"


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
        if not request.url.path.endswith(_DOCS_PATH_SUFFIXES):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
        if request.url.path.startswith(_AUTH_PATH_PREFIX):
            response.headers["Cache-Control"] = "no-store"
        return response
