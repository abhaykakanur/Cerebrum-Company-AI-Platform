"""The single source of truth for middleware ordering.

CIS Phase 1 Prompt 3 Section 3 fixed the original pipeline order: Trusted
Host, Security Headers, Compression, CORS, Request ID, Correlation ID,
Request Context, Request Timer, Structured Logging, (Exception Handler —
registered separately, see cerebrum.core.exception_handlers), Router. CIS
Phase 1 Prompt 5 inserts two more: Request Size Limit (after Security
Headers — reject an oversized body before any further processing spends
work on it) and Authentication (after Correlation ID, before Request
Context — so Request Context can fold the resolved identity into
:class:`~cerebrum.middleware.context.RequestContext`; see
cerebrum.middleware.authentication's docstring). CIS Phase 1 Prompt 6
inserts one more: API Metrics (innermost of all, right beside Structured
Logging — both need the final response and the bound
:class:`~cerebrum.middleware.context.RequestContext`'s ``elapsed_ms``,
which only exists once Request Context has run).

Starlette's ``Starlette.add_middleware`` inserts each call at the FRONT
of its internal list (``self.user_middleware.insert(0, ...)``), and then
builds the ASGI stack by wrapping outward from the router using that list
reversed. Net effect, verified empirically (see
apps/backend/tests/unit/test_middleware.py): the LAST ``add_middleware``
call becomes the OUTERMOST layer and therefore runs FIRST on every
request — the opposite of call order. To make the calls below execute in
the order stated above, they are issued in the REVERSE of that order:
Structured Logging is registered first (innermost, runs last, closest to
the Router) and Trusted Host is registered last (outermost, runs first).
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cerebrum.config.settings import Settings
from cerebrum.infrastructure.security.jwt import TokenService
from cerebrum.middleware.authentication import AuthenticationMiddleware
from cerebrum.middleware.correlation_id import CorrelationIDMiddleware
from cerebrum.middleware.logging import StructuredLoggingMiddleware
from cerebrum.middleware.metrics import APIMetricsMiddleware
from cerebrum.middleware.request_context import RequestContextMiddleware
from cerebrum.middleware.request_id import RequestIDMiddleware
from cerebrum.middleware.request_size_limit import RequestSizeLimitMiddleware
from cerebrum.middleware.request_timing import RequestTimingMiddleware
from cerebrum.middleware.security_headers import SecurityHeadersMiddleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Registers every platform middleware. Calls are issued innermost
    (closest to the Router) first — see this module's docstring for why.
    """
    # 12. Structured Logging — registered first => innermost => runs last
    #     on the request path, observing every other middleware's effect
    #     on the response before logging it.
    app.add_middleware(StructuredLoggingMiddleware)
    # 11. API Metrics
    app.add_middleware(APIMetricsMiddleware)
    # 10. Request Timer
    app.add_middleware(RequestTimingMiddleware)
    # 9. Request Context
    app.add_middleware(
        RequestContextMiddleware,
        environment=settings.application.environment,
        trusted_proxies=settings.security.trusted_proxies,
    )
    # 8. Authentication — resolves identity for Request Context to fold in.
    app.add_middleware(
        AuthenticationMiddleware, token_service=TokenService(settings.security)
    )
    # 7. Correlation ID
    app.add_middleware(CorrelationIDMiddleware)
    # 6. Request ID
    app.add_middleware(RequestIDMiddleware)
    # 5. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Response-Time-Ms"],
    )
    # 4. Compression
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    # 3. Request Size Limit
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_bytes=settings.security.max_request_body_bytes,
    )
    # 2. Security Headers
    app.add_middleware(
        SecurityHeadersMiddleware, environment=settings.application.environment
    )
    # 1. Trusted Host — registered last => outermost => runs first on the
    #    request path, per the spec's stated order.
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.security.trusted_hosts
    )
    # 13. Exception Handler — registered via cerebrum.core.exception_handlers,
    #     not app.add_middleware; Starlette places its ExceptionMiddleware
    #     innermost automatically, immediately outside the Router, which
    #     already matches this pipeline's intended position.
    # 14. Router — registered via cerebrum.core.routers.
