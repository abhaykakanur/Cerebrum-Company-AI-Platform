"""Proves CIS Phase 1 Prompt 6's Response Standardization acceptance
criterion: cerebrum.api.response_builder fills every request-scoped
envelope field (Request ID, Correlation ID, Version) automatically, and
correctly adapts a repository-layer
:class:`~cerebrum.repositories.contracts.Page` into
:class:`~cerebrum.api.schemas.envelope.PaginationMeta`.
"""

import pytest

from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.config.settings import Settings
from cerebrum.middleware.context import (
    RequestContext,
    bind_request_context,
    reset_request_context,
)
from cerebrum.repositories.contracts import Page, Pagination

pytestmark = pytest.mark.unit


def _bound_context() -> RequestContext:
    return RequestContext(
        request_id="req-123",
        correlation_id="corr-456",
        method="GET",
        path="/test",
        client_ip=None,
        user_agent=None,
        environment="testing",
    )


def test_build_success_response_fills_request_scoped_fields(settings: Settings) -> None:
    token = bind_request_context(_bound_context())
    try:
        response = build_success_response({"a": 1}, settings=settings)
    finally:
        reset_request_context(token)

    assert response.data == {"a": 1}
    assert response.request_id == "req-123"
    assert response.correlation_id == "corr-456"
    assert response.version == settings.application.version
    assert response.pagination is None


def test_build_success_response_carries_message_and_metadata(
    settings: Settings,
) -> None:
    token = bind_request_context(_bound_context())
    try:
        response = build_success_response(
            {"a": 1}, settings=settings, message="ok", metadata={"count": 1}
        )
    finally:
        reset_request_context(token)

    assert response.message == "ok"
    assert response.metadata == {"count": 1}


def test_build_success_response_requires_an_active_request_context(
    settings: Settings,
) -> None:
    with pytest.raises(RuntimeError):
        build_success_response({"a": 1}, settings=settings)


def test_build_collection_response_computes_pagination_meta(settings: Settings) -> None:
    page = Page(
        items=["a", "b"], total_items=25, pagination=Pagination(page=2, page_size=10)
    )
    token = bind_request_context(_bound_context())
    try:
        response = build_collection_response(page, settings=settings)
    finally:
        reset_request_context(token)

    assert response.data == ["a", "b"]
    assert response.pagination is not None
    assert response.pagination.page == 2
    assert response.pagination.page_size == 10
    assert response.pagination.total_items == 25
    assert response.pagination.total_pages == 3
    assert response.pagination.has_next is True
    assert response.pagination.has_previous is True
