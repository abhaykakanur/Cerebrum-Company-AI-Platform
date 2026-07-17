"""Builds the request's :class:`~cerebrum.middleware.context.RequestContext`
from the identifiers RequestIDMiddleware and CorrelationIDMiddleware
already attached to ``request.state``, then binds it to the contextvar
for the duration of the request.

Must run after RequestIDMiddleware and CorrelationIDMiddleware, and
before RequestTimingMiddleware/StructuredLoggingMiddleware — see
cerebrum.middleware.registry for the enforced order.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from cerebrum.config.environment import Environment
from cerebrum.middleware.context import (
    RequestContext,
    bind_request_context,
    reset_request_context,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assembles and binds the per-request :class:`RequestContext`."""

    def __init__(self, app: ASGIApp, *, environment: Environment) -> None:
        super().__init__(app)
        self._environment = environment

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        context = RequestContext(
            request_id=request.state.request_id,
            correlation_id=request.state.correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            environment=self._environment.value,
        )
        request.state.cerebrum_context = context
        token = bind_request_context(context)
        try:
            return await call_next(request)
        finally:
            reset_request_context(token)
