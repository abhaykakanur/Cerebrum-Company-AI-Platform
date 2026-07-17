"""Structured request/response logging: the last middleware before the
Router, so it observes the final response status of everything upstream
(including exception handling — see cerebrum.core.exception_handlers,
which runs inside Starlette's innermost ExceptionMiddleware layer).

See CIS Phase 1 Prompt 3 Section 3's Structured Logging requirement:
every log entry is JSON, and includes Request ID, Correlation ID, and
elapsed time via the bound
:class:`~cerebrum.middleware.context.RequestContext`.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from cerebrum.core.logging import get_api_logger

_logger = get_api_logger()


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Emits one structured log entry per request, on completion."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        context = request.state.cerebrum_context
        log = _logger.bind(
            request_id=context.request_id,
            correlation_id=context.correlation_id,
            method=context.method,
            path=context.path,
        )
        response = await call_next(request)
        log.info(
            "request.completed",
            status_code=response.status_code,
            duration_ms=round(context.elapsed_ms, 2),
        )
        return response
