"""Builds the standard
:class:`~cerebrum.api.schemas.envelope.SuccessResponse` envelope with its
request-scoped fields (Request ID, Correlation ID, Version) filled in
automatically, so a future endpoint never constructs those by hand — see
docs/architecture/specification/81_API_Standards.md's Response Standards
("a partial implementation ... breaks the Consistency principle").

``cerebrum.api.health`` and ``cerebrum.api.v1.auth`` deliberately return
unwrapped shapes for reasons specific to each (orchestrator convention;
OAuth2 Password Flow / Swagger UI's "Authorize" popup — see their own
module docstrings) and are not retrofit to use this builder. Every other
future endpoint SHOULD.
"""

from cerebrum.api.schemas.envelope import PaginationMeta, SuccessResponse
from cerebrum.config.settings import Settings
from cerebrum.middleware.context import get_current_request_context
from cerebrum.repositories.contracts import Page


def _current_identifiers() -> tuple[str, str | None]:
    context = get_current_request_context()
    if context is None:
        raise RuntimeError(
            "build_success_response()/build_collection_response() require an "
            "active request context — see cerebrum.middleware.request_context."
        )
    return context.request_id, context.correlation_id


def build_success_response[DataT](
    data: DataT,
    *,
    settings: Settings,
    message: str | None = None,
    metadata: dict[str, object] | None = None,
) -> SuccessResponse[DataT]:
    """The envelope for a single-resource response."""
    request_id, correlation_id = _current_identifiers()
    return SuccessResponse(
        data=data,
        message=message,
        metadata=metadata,
        request_id=request_id,
        correlation_id=correlation_id,
        version=settings.application.version,
    )


def build_collection_response[DataT](
    page: Page[DataT],
    *,
    settings: Settings,
    message: str | None = None,
    metadata: dict[str, object] | None = None,
) -> SuccessResponse[list[DataT]]:
    """The envelope for a collection response, with
    :class:`~cerebrum.api.schemas.envelope.PaginationMeta` computed from
    the repository-layer :class:`~cerebrum.repositories.contracts.Page`
    returned by a ``list()`` call.
    """
    request_id, correlation_id = _current_identifiers()
    pagination_meta = PaginationMeta(
        page=page.pagination.page,
        page_size=page.pagination.page_size,
        total_items=page.total_items,
        total_pages=page.total_pages,
        has_next=page.has_next,
        has_previous=page.has_previous,
    )
    return SuccessResponse(
        data=page.items,
        message=message,
        metadata=metadata,
        pagination=pagination_meta,
        request_id=request_id,
        correlation_id=correlation_id,
        version=settings.application.version,
    )
