"""The single source of truth for middleware ordering.

CIS Phase 1 Prompt 3 Section 3 fixes the pipeline order exactly: Trusted
Host, Security Headers, Compression, CORS, Request ID, Correlation ID,
Request Context, Request Timer, Structured Logging, (Exception Handler —
registered separately, see cerebrum.core.exception_handlers), Router.

Starlette's ``Starlette.add_middleware`` inserts each call at the FRONT
of its internal list (``self.user_middleware.insert(0, ...)``), and then
builds the ASGI stack by wrapping outward from the router using that list
reversed. Net effect, verified empirically (see
apps/backend/tests/unit/test_middleware.py): the LAST ``add_middleware``
call becomes the OUTERMOST layer and therefore runs FIRST on every
request — the opposite of call order. To make the calls below execute in
the spec's stated order, they are issued in the REVERSE of that order:
Structured Logging is registered first (innermost, runs last, closest to
the Router) and Trusted Host is registered last (outermost, runs first).
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cerebrum.config.settings import Settings
from cerebrum.middleware.correlation_id import CorrelationIDMiddleware
from cerebrum.middleware.logging import StructuredLoggingMiddleware
from cerebrum.middleware.request_context import RequestContextMiddleware
from cerebrum.middleware.request_id import RequestIDMiddleware
from cerebrum.middleware.request_timing import RequestTimingMiddleware
from cerebrum.middleware.security_headers import SecurityHeadersMiddleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Registers every platform middleware. Calls are issued innermost
    (closest to the Router) first — see this module's docstring for why.
    """
    # 9. Structured Logging — registered first => innermost => runs last on
    #    the request path, observing every other middleware's effect on
    #    the response before logging it.
    app.add_middleware(StructuredLoggingMiddleware)
    # 8. Request Timer
    app.add_middleware(RequestTimingMiddleware)
    # 7. Request Context
    app.add_middleware(
        RequestContextMiddleware, environment=settings.application.environment
    )
    # 6. Correlation ID
    app.add_middleware(CorrelationIDMiddleware)
    # 5. Request ID
    app.add_middleware(RequestIDMiddleware)
    # 4. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Response-Time-Ms"],
    )
    # 3. Compression
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    # 2. Security Headers
    app.add_middleware(
        SecurityHeadersMiddleware, environment=settings.application.environment
    )
    # 1. Trusted Host — registered last => outermost => runs first on the
    #    request path, per the spec's stated order.
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.security.trusted_hosts
    )
    # 10. Exception Handler — registered via cerebrum.core.exception_handlers,
    #     not app.add_middleware; Starlette places its ExceptionMiddleware
    #     innermost automatically, immediately outside the Router, which
    #     already matches this pipeline's intended position.
    # 11. Router — registered via cerebrum.core.routers.
