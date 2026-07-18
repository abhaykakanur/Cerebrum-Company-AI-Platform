"""Standard error-response OpenAPI documentation, reused across routers
via ``APIRouter(..., responses=STANDARD_ERROR_RESPONSES)`` — FastAPI
merges a router's ``responses`` into every route it owns, and a route's
own ``responses=`` (if any) takes precedence per-status-code. This is CIS
Phase 1 Prompt 6's OpenAPI "Error documentation"/"Response schemas"
requirement and
docs/architecture/specification/81_API_Standards.md's Response
Standards ("Error responses follow this same Response Standards
envelope") made visible in the generated schema, without hand-rolling
OpenAPI JSON or re-declaring the same six status codes on every route.
"""

from typing import Any

from cerebrum.api.schemas.envelope import ErrorResponse

STANDARD_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "description": "Authentication failed or no credentials were provided.",
    },
    403: {
        "model": ErrorResponse,
        "description": "The authenticated caller lacks the required permission.",
    },
    404: {
        "model": ErrorResponse,
        "description": "The requested resource does not exist.",
    },
    422: {"model": ErrorResponse, "description": "Request validation failed."},
    429: {
        "model": ErrorResponse,
        "description": "The caller exceeded a configured rate limit.",
    },
    500: {
        "model": ErrorResponse,
        "description": "An unexpected server error occurred.",
    },
}
