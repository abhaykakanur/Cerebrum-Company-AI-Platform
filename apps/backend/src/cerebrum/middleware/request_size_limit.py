"""Request size limits: rejects a request whose declared body size
exceeds ``SecuritySettings.max_request_body_bytes`` before any further
processing reads it.

Checks ``Content-Length`` only — a request that omits it and streams an
oversized chunked body past this check is a known gap at this milestone
(Deferred to Architecture; would need a streaming byte-counter wrapping
the ASGI receive channel). Every request this codebase's own clients
send declares ``Content-Length``; this middleware protects against the
common case (an oversized upload/payload), not an adversarial streaming
client.
"""

from collections.abc import Awaitable, Callable

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        super().__init__(app)
        self._max_body_bytes = max_body_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None
            if declared_size is not None and declared_size > self._max_body_bytes:
                # See cerebrum.middleware.authentication's docstring:
                # exceptions raised here would bypass every registered
                # exception handler, so the standardized envelope is
                # built directly instead of raised-and-caught.
                from cerebrum.core.exception_handlers import build_error_response

                return build_error_response(
                    request,
                    error_code="REQUEST_ENTITY_TOO_LARGE",
                    message=(
                        f"Request body exceeds the {self._max_body_bytes}-byte limit."
                    ),
                    http_status=status.HTTP_413_CONTENT_TOO_LARGE,
                )
        return await call_next(request)
