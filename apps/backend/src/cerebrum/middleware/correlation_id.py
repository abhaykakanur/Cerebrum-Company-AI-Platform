"""Correlation ID propagation: reused from the client's ``X-Correlation-ID``
header when supplied, generated otherwise. Always echoed back.

See CIS Phase 1 Prompt 3 Section 3's Correlation ID requirement and
docs/architecture/specification/81_API_Standards.md's Definitions (a
Correlation ID may be client-supplied to link related requests; a
Request ID is always server-assigned — see request_id.py).
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from cerebrum.utils.identifiers import generate_correlation_id

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Reuses an inbound Correlation ID, or generates one."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = (
            request.headers.get(CORRELATION_ID_HEADER) or generate_correlation_id()
        )
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
