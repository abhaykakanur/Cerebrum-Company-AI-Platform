"""Proves CIS Phase 1 Prompt 6's Pagination/Filtering/Sorting Foundation
acceptance criteria: the HTTP query-parameter dependencies in
cerebrum.dependencies.pagination correctly translate raw query strings
into cerebrum.repositories.contracts's datastore-agnostic
Pagination/SortSpec/FilterSpec — see that module's docstring for why no
repository call happens here.
"""

import pytest

from cerebrum.dependencies.pagination import get_filters, get_pagination, get_sort
from cerebrum.repositories.contracts import FilterOperator, Pagination, SortDirection
from cerebrum.shared.errors.exceptions import ValidationException

pytestmark = pytest.mark.unit


def test_get_pagination_defaults() -> None:
    assert get_pagination() == Pagination(page=1, page_size=50)


def test_get_pagination_uses_supplied_values() -> None:
    assert get_pagination(page=3, page_size=10) == Pagination(page=3, page_size=10)


def test_get_sort_returns_empty_list_when_absent() -> None:
    assert get_sort(None) == []


def test_get_sort_parses_ascending_field() -> None:
    specs = get_sort("name")
    assert len(specs) == 1
    assert specs[0].field == "name"
    assert specs[0].direction == SortDirection.ASC


def test_get_sort_parses_descending_field() -> None:
    specs = get_sort("-created_at")
    assert specs[0].field == "created_at"
    assert specs[0].direction == SortDirection.DESC


def test_get_sort_parses_multiple_fields() -> None:
    specs = get_sort("name,-created_at")
    assert [(s.field, s.direction) for s in specs] == [
        ("name", SortDirection.ASC),
        ("created_at", SortDirection.DESC),
    ]


def test_get_sort_ignores_blank_segments() -> None:
    specs = get_sort("name,,")
    assert len(specs) == 1


def test_get_filters_returns_empty_list_when_absent() -> None:
    assert get_filters(None) == []


def test_get_filters_parses_a_single_filter() -> None:
    specs = get_filters(["status:eq:active"])
    assert len(specs) == 1
    assert specs[0].field == "status"
    assert specs[0].operator == FilterOperator.EQ
    assert specs[0].value == "active"


def test_get_filters_parses_multiple_filters() -> None:
    specs = get_filters(["status:eq:active", "created_at:gte:2024-01-01"])
    assert len(specs) == 2


def test_get_filters_coerces_in_operator_to_a_list() -> None:
    specs = get_filters(["status:in:active,pending,archived"])
    assert specs[0].operator == FilterOperator.IN
    assert specs[0].value == ["active", "pending", "archived"]


def test_get_filters_rejects_malformed_filter() -> None:
    with pytest.raises(ValidationException):
        get_filters(["not-enough-parts"])


def test_get_filters_rejects_unknown_operator() -> None:
    with pytest.raises(ValidationException):
        get_filters(["status:bogus:active"])


def test_get_filters_value_may_itself_contain_colons() -> None:
    # split(":", 2) — only the first two colons are structural.
    specs = get_filters(["url:eq:https://example.com"])
    assert specs[0].value == "https://example.com"
