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
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from cerebrum.api.schemas.envelope import ErrorDetail, ErrorResponse
from cerebrum.config.settings import Settings, get_settings
from cerebrum.core.logging import get_api_logger
from cerebrum.middleware.context import get_current_request_context
from cerebrum.shared.errors.base import PlatformException
from cerebrum.shared.errors.exceptions import RateLimitExceededException

_logger = get_api_logger()


def _identifiers(request: Request) -> tuple[str, str | None]:
    """Best-effort Request ID / Correlation ID lookup for a handler that
    may run before RequestContextMiddleware has bound a context — either
    a malformed request that fails ASGI-level parsing, or (as of CIS
    Phase 1 Prompt 5) an exception raised from within
    cerebrum.middleware.authentication, which runs before Request
    Context in the pipeline (see cerebrum.middleware.registry). Falls
    back to ``request.state``, which RequestIDMiddleware/CorrelationIDMiddleware
    populate earlier in the pipeline than RequestContextMiddleware binds
    the contextvar, before finally falling back to ``"unknown"``.
    """
    context = get_current_request_context()
    if context is not None:
        return context.request_id, context.correlation_id
    return getattr(request.state, "request_id", "unknown"), getattr(
        request.state, "correlation_id", None
    )


def build_error_response(
    request: Request,
    *,
    error_code: str,
    message: str,
    http_status: int,
    retryable: bool = False,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    """The standardized :class:`~cerebrum.api.schemas.envelope.ErrorResponse`
    builder every handler below uses. Public — and reused directly (not
    only through a raised :class:`~cerebrum.shared.errors.base.PlatformException`)
    by middleware that must reject a request before any exception
    handler can see it, e.g.
    cerebrum.middleware.request_size_limit.RequestSizeLimitMiddleware —
    see cerebrum.middleware.authentication's docstring for why exceptions
    raised inside ``BaseHTTPMiddleware.dispatch()`` bypass
    ``@app.exception_handler`` entirely.
    """
    request_id, correlation_id = _identifiers(request)
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


async def handle_platform_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PlatformException)
    _logger.error(
        "exception.platform",
        error_code=exc.error_code,
        category=exc.category.value,
        severity=exc.severity.value,
        message=exc.message,
        context=exc.context,
    )
    response = build_error_response(
        request,
        error_code=exc.error_code,
        message=exc.message,
        http_status=exc.http_status,
        retryable=exc.retryable,
    )
    if isinstance(exc, RateLimitExceededException):
        # Graceful throttling per
        # docs/architecture/specification/81_API_Standards.md's Rate
        # Limiting section: an early, standard signal for when to retry,
        # not just a bare 429.
        response.headers["Retry-After"] = str(exc.retry_after_seconds)
    return response


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]), message=error["msg"]
        )
        for error in exc.errors()
    ]
    _logger.warning("exception.validation", errors=details)
    return build_error_response(
        request,
        error_code="REQUEST_VALIDATION_ERROR",
        message="Request validation failed.",
        http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
    )


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    _logger.info("exception.http", status_code=exc.status_code, detail=exc.detail)
    return build_error_response(
        request,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        http_status=exc.status_code,
    )


async def handle_stale_data_error(request: Request, exc: Exception) -> JSONResponse:
    """CIS Phase 2 Prompt 1's Optimistic Locking: SQLAlchemy's
    ``version_id_col`` mechanism (see
    cerebrum.infrastructure.database.models.mixins.OptimisticLockMixin)
    raises this plain SQLAlchemy exception, not a
    :class:`~cerebrum.shared.errors.base.PlatformException`, when an
    ``UPDATE`` targets a row another transaction already changed —
    translated here into the same standardized 409 envelope
    :class:`~cerebrum.shared.errors.exceptions.ConflictException` would
    produce, rather than falling through to
    :func:`handle_unexpected_exception`'s generic 500.
    """
    assert isinstance(exc, StaleDataError)
    _logger.warning("exception.optimistic_lock_conflict", message=str(exc))
    return build_error_response(
        request,
        error_code="ConflictException",
        message="The resource was modified by another request. Reload and retry.",
        http_status=status.HTTP_409_CONFLICT,
        retryable=True,
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


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    settings = get_settings()
    _logger.exception("exception.unexpected", exception_type=type(exc).__name__)
    return build_error_response(
        request,
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
    app.add_exception_handler(StaleDataError, handle_stale_data_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
