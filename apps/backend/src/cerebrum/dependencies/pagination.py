"""Query-parameter dependencies for Offset Pagination, Sorting, and
Filtering (CIS Phase 1 Prompt 6) — the HTTP-layer translation from raw
query strings into the datastore-agnostic
:class:`~cerebrum.repositories.contracts.Pagination`/:class:`~cerebrum.repositories.contracts.SortSpec`/:class:`~cerebrum.repositories.contracts.FilterSpec`
contracts CIS Phase 1 Prompt 4 already defined. No repository or business
query is implemented here — a future route depends on
:data:`PaginationDep`/:data:`SortDep`/:data:`FilterDep` and passes the
results straight to a repository's ``list()``, exactly as
cerebrum.repositories.postgres.role_repository/audit_repository already
consume :class:`~cerebrum.repositories.contracts.Pagination` today.
"""

from typing import Annotated

from fastapi import Depends, Query

from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Pagination,
    SortDirection,
    SortSpec,
)
from cerebrum.shared.errors.exceptions import ValidationException

# Mirrors Pagination.__post_init__'s own ceiling — declared again here so
# an out-of-range page_size is rejected by FastAPI's request validation
# (a 422 with a field-level detail) before it ever reaches Pagination's
# constructor, giving the caller a more specific error than a generic
# ValueError would.
_MAX_PAGE_SIZE = 500


def get_pagination(
    page: Annotated[int, Query(ge=1, description="1-indexed page number.")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=_MAX_PAGE_SIZE, description="Items per page.")
    ] = 50,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


def get_sort(
    sort: Annotated[
        str | None,
        Query(
            description="Comma-separated field list; prefix a field with '-' for "
            "descending, e.g. 'name,-created_at'."
        ),
    ] = None,
) -> list[SortSpec]:
    if not sort:
        return []
    specs: list[SortSpec] = []
    for raw_field in sort.split(","):
        field = raw_field.strip()
        if not field:
            continue
        if field.startswith("-"):
            specs.append(SortSpec(field=field[1:], direction=SortDirection.DESC))
        else:
            specs.append(SortSpec(field=field, direction=SortDirection.ASC))
    return specs


SortDep = Annotated[list[SortSpec], Depends(get_sort)]


def _coerce_filter_value(operator: FilterOperator, raw_value: str) -> object:
    """:attr:`~cerebrum.repositories.contracts.FilterOperator.IN` is the
    one operator whose value is itself a list — every other operator's
    value passes through as the raw string, since
    cerebrum.repositories.postgres.query_utils's SQLAlchemy translation
    (and any future non-SQL translation) is responsible for coercing it
    to the target column's type.
    """
    if operator is FilterOperator.IN:
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    return raw_value


def get_filters(
    filter_: Annotated[
        list[str] | None,
        Query(
            alias="filter",
            description="Repeatable 'field:operator:value' filter, e.g. "
            "'status:eq:active'. Valid operators: eq, neq, gt, gte, lt, lte, in, "
            "contains. 'in' takes a comma-separated value list.",
        ),
    ] = None,
) -> list[FilterSpec]:
    if not filter_:
        return []
    specs: list[FilterSpec] = []
    for raw in filter_:
        parts = raw.split(":", 2)
        if len(parts) != 3:
            raise ValidationException(
                f"Malformed filter '{raw}'; expected 'field:operator:value'.",
                context={"filter": raw},
            )
        field, raw_operator, raw_value = parts
        try:
            operator = FilterOperator(raw_operator)
        except ValueError as exc:
            raise ValidationException(
                f"Unknown filter operator '{raw_operator}' in '{raw}'.",
                context={"filter": raw, "operator": raw_operator},
            ) from exc
        specs.append(
            FilterSpec(
                field=field,
                operator=operator,
                value=_coerce_filter_value(operator, raw_value),
            )
        )
    return specs


FilterDep = Annotated[list[FilterSpec], Depends(get_filters)]
