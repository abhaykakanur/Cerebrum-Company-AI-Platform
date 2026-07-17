"""Request ID assignment: every incoming request receives a UUIDv4
Request ID; every response returns it via the ``X-Request-ID`` header.

See CIS Phase 1 Prompt 3 Section 3's Request ID requirement. Runs before
CorrelationIDMiddleware and RequestContextMiddleware in the pipeline (see
cerebrum.middleware.registry) — those depend on ``request.state.request_id``
already being set.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from cerebrum.utils.identifiers import generate_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a server-generated Request ID, unconditionally — unlike
    Correlation ID, a Request ID is never accepted from the client, since
    it must uniquely identify this server's processing of the request.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = generate_request_id()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
