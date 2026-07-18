"""Translates the datastore-agnostic
:class:`~cerebrum.repositories.contracts.FilterSpec`/:class:`~cerebrum.repositories.contracts.SortSpec`
contracts into SQLAlchemy ``WHERE``/``ORDER BY`` clauses — written once
here so every PostgreSQL repository's ``list()`` implementation shares
the same translation instead of five near-identical ones, per CIS Phase
1 Prompt 4's "no duplicated code" quality standard.
"""

from typing import Any

from sqlalchemy import Select
from sqlalchemy.orm import DeclarativeBase

from cerebrum.repositories.contracts import (
    FilterOperator,
    FilterSpec,
    Pagination,
    SortSpec,
)
from cerebrum.shared.errors.exceptions import ValidationException

_OPERATOR_APPLIERS = {
    FilterOperator.EQ: lambda column, value: column == value,
    FilterOperator.NEQ: lambda column, value: column != value,
    FilterOperator.GT: lambda column, value: column > value,
    FilterOperator.GTE: lambda column, value: column >= value,
    FilterOperator.LT: lambda column, value: column < value,
    FilterOperator.LTE: lambda column, value: column <= value,
    FilterOperator.IN: lambda column, value: column.in_(value),
    FilterOperator.CONTAINS: lambda column, value: column.contains(value),
}


def _column(model: type[DeclarativeBase], field: str) -> Any:
    try:
        return getattr(model, field)
    except AttributeError as exc:
        raise ValidationException(
            f"'{field}' is not a queryable field on {model.__name__}.",
            context={"model": model.__name__, "field": field},
        ) from exc


def apply_filters(
    statement: Select[Any],
    model: type[DeclarativeBase],
    filters: list[FilterSpec] | None,
) -> Select[Any]:
    """Applies every filter with logical AND — matching
    docs/architecture/specification/81_API_Standards.md's "Combined
    Filters" default, per cerebrum.repositories.contracts's docstring.
    """
    for filter_spec in filters or []:
        column = _column(model, filter_spec.field)
        statement = statement.where(
            _OPERATOR_APPLIERS[filter_spec.operator](column, filter_spec.value)
        )
    return statement


def apply_sort(
    statement: Select[Any], model: type[DeclarativeBase], sort: list[SortSpec] | None
) -> Select[Any]:
    for sort_spec in sort or []:
        column = _column(model, sort_spec.field)
        statement = statement.order_by(
            column.desc() if sort_spec.direction.value == "desc" else column.asc()
        )
    return statement


def apply_pagination(statement: Select[Any], pagination: Pagination) -> Select[Any]:
    """``OFFSET``/``LIMIT``, written once here so every PostgreSQL
    repository's ``list()`` shares the same translation instead of
    repeating ``.offset(...).limit(...)`` — see this module's docstring.
    """
    return statement.offset(pagination.offset).limit(pagination.page_size)
