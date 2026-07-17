"""The Logger dependency provider — a "Scoped" lifetime: a fresh
bound-logger instance per request, carrying that request's Request ID
and Correlation ID automatically on every field it logs, so a route
handler never re-attaches them by hand.
"""

from typing import Annotated

from fastapi import Depends, Request
from structlog.typing import FilteringBoundLogger

from cerebrum.core.logging import get_logger


def get_request_logger(request: Request) -> FilteringBoundLogger:
    context = getattr(request.state, "cerebrum_context", None)
    logger = get_logger("cerebrum.api")
    if context is not None:
        logger = logger.bind(
            request_id=context.request_id, correlation_id=context.correlation_id
        )
    return logger


RequestLoggerDep = Annotated[FilteringBoundLogger, Depends(get_request_logger)]
