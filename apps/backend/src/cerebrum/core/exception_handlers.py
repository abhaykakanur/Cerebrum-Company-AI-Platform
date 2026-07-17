"""The single centralized exception handler set.

See CIS Phase 1 Prompt 3 Section 3's Global Exception Handler
requirement: capture, log, map, and return a standardized
:class:`~cerebrum.api.schemas.envelope.ErrorResponse` — never an internal
stack trace in a production-like environment. Every handler here maps
one exception type to that same envelope; no route or service SHALL
build its own ad hoc error response.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cerebrum.api.schemas.envelope import ErrorDetail, ErrorResponse
from cerebrum.config.settings import Settings, get_settings
from cerebrum.core.logging import get_api_logger
from cerebrum.middleware.context import get_current_request_context
from cerebrum.shared.errors.base import PlatformException

_logger = get_api_logger()


def _identifiers() -> tuple[str, str | None]:
    """Best-effort Request ID / Correlation ID lookup for a handler that
    may run before RequestContextMiddleware has bound a context (e.g. a
    malformed request that fails ASGI-level parsing).
    """
    context = get_current_request_context()
    if context is None:
        return "unknown", None
    return context.request_id, context.correlation_id


def _envelope(
    *,
    error_code: str,
    message: str,
    http_status: int,
    retryable: bool = False,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    request_id, correlation_id = _identifiers()
    settings = get_settings()
    body = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        retryable=retryable,
        request_id=request_id,
        correlation_id=correlation_id,
        version=settings.application.version,
    )
    return JSONResponse(status_code=http_status, content=body.model_dump(mode="json"))


async def handle_platform_exception(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PlatformException)
    _logger.error(
        "exception.platform",
        error_code=exc.error_code,
        category=exc.category.value,
        severity=exc.severity.value,
        message=exc.message,
        context=exc.context,
    )
    return _envelope(
        error_code=exc.error_code,
        message=exc.message,
        http_status=exc.http_status,
        retryable=exc.retryable,
    )


async def handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]), message=error["msg"]
        )
        for error in exc.errors()
    ]
    _logger.warning("exception.validation", errors=details)
    return _envelope(
        error_code="REQUEST_VALIDATION_ERROR",
        message="Request validation failed.",
        http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
    )


async def handle_http_exception(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    _logger.info("exception.http", status_code=exc.status_code, detail=exc.detail)
    return _envelope(
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        http_status=exc.status_code,
    )


def _unexpected_exception_message(exc: Exception, settings: Settings) -> str:
    """Never expose internal stack traces in a production-like
    environment — see CIS Phase 1 Prompt 3 Section 3's Global Exception
    Handler requirement. Development/testing include the exception's own
    message for developer convenience; the full traceback is always
    logged server-side (see :func:`handle_unexpected_exception`), never
    only available via the response body.
    """
    if settings.application.environment.is_production_like:
        return "An unexpected error occurred."
    return f"An unexpected error occurred: {exc}"


async def handle_unexpected_exception(
    _request: Request, exc: Exception
) -> JSONResponse:
    settings = get_settings()
    _logger.exception("exception.unexpected", exception_type=type(exc).__name__)
    return _envelope(
        error_code="UNEXPECTED_ERROR",
        message=_unexpected_exception_message(exc, settings),
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers every handler above. Order matters only in that FastAPI
    matches the most specific registered type first, then falls back to
    ``Exception`` — see FastAPI's exception-handler resolution.
    """
    app.add_exception_handler(PlatformException, handle_platform_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_exception)
