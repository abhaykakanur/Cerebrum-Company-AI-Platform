"""Response timing: adds an ``X-Response-Time-Ms`` header. Must run after
RequestContextMiddleware, whose :class:`~cerebrum.middleware.context.RequestContext`
already tracks ``start_time`` — this middleware only reads it, it does not
duplicate timer state.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

RESPONSE_TIME_HEADER = "X-Response-Time-Ms"


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Reports elapsed request-processing time on the response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        context = request.state.cerebrum_context
        response.headers[RESPONSE_TIME_HEADER] = f"{context.elapsed_ms:.2f}"
        return response
