"""Proves the acceptance criterion for the Repository Foundation from CIS
Phase 1 Prompt 4: pagination/filtering/sorting/soft-delete contracts
exist and behave correctly, and the abstract CRUD contract cannot be
instantiated without a concrete implementation.
"""

from dataclasses import FrozenInstanceError

import pytest

from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Page,
    Pagination,
    SortDirection,
    SortSpec,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository

pytestmark = pytest.mark.unit


def test_pagination_computes_offset() -> None:
    assert Pagination(page=1, page_size=50).offset == 0
    assert Pagination(page=3, page_size=20).offset == 40


def test_pagination_rejects_invalid_page() -> None:
    with pytest.raises(ValueError, match="page"):
        Pagination(page=0)


def test_pagination_rejects_out_of_range_page_size() -> None:
    with pytest.raises(ValueError, match="page_size"):
        Pagination(page_size=501)


def test_pagination_is_immutable() -> None:
    pagination = Pagination()
    with pytest.raises(FrozenInstanceError):
        pagination.page = 2  # type: ignore[misc]


def test_page_computes_total_pages_and_navigation() -> None:
    page = Page(
        items=["a", "b"], total_items=25, pagination=Pagination(page=2, page_size=10)
    )
    assert page.total_pages == 3
    assert page.has_next is True
    assert page.has_previous is True


def test_page_with_zero_items_has_zero_pages() -> None:
    page = Page(items=[], total_items=0, pagination=Pagination())
    assert page.total_pages == 0
    assert page.has_next is False
    assert page.has_previous is False


def test_sort_spec_defaults_to_ascending() -> None:
    assert SortSpec(field="created_at").direction == SortDirection.ASC


def test_filter_spec_carries_operator_and_value() -> None:
    spec = FilterSpec(field="status", operator=FilterOperator.EQ, value="active")
    assert spec.operator == FilterOperator.EQ


def test_abstract_repository_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        AbstractRepository()  # type: ignore[abstract]


def test_soft_delete_repository_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        SoftDeleteRepository()  # type: ignore[abstract]


def test_concrete_repository_must_implement_every_abstract_method() -> None:
    class _IncompleteRepository(AbstractRepository[str, int]):
        async def get_by_id(self, entity_id: int) -> str | None:
            return None

        # add/update/delete/list intentionally left unimplemented.

    with pytest.raises(TypeError):
        _IncompleteRepository()  # type: ignore[abstract]
