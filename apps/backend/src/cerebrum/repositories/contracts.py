"""Pagination, filtering, and sorting contracts every repository
implementation accepts and returns — defined once here so a future
PostgreSQL repository, a future Neo4j repository, and a future Qdrant
repository all expose the same query shape to their callers, per CIS
Phase 1 Prompt 4's "no duplicated code" quality standard.

Distinct from ``cerebrum.api.schemas.envelope.PaginationMeta``: that type
is the HTTP *response* shape (presentation layer); this module's
:class:`Page` is the repository-layer *return* shape an application
service adapts into that response — infrastructure/repositories/ must
not import from api/, per docs/architecture/dependency-rules.md.
"""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Pagination:
    """An offset-pagination request. Cursor pagination (per
    docs/architecture/specification/81_API_Standards.md, required for
    large/frequently-changing result sets) is Deferred to the first
    repository that needs it — this contract does not yet define a
    cursor-based variant.
    """

    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if not (1 <= self.page_size <= 500):
            raise ValueError("page_size must be between 1 and 500")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class Page[EntityT]:
    """One page of repository results, with enough metadata for a
    caller to compute the rest of
    :class:`~cerebrum.api.schemas.envelope.PaginationMeta`.
    """

    items: list[EntityT]
    total_items: int
    pagination: Pagination

    @property
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 0
        return -(-self.total_items // self.pagination.page_size)  # ceil division

    @property
    def has_next(self) -> bool:
        return self.pagination.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.pagination.page > 1


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class SortSpec:
    """One field to sort by. A repository call accepts ``list[SortSpec]``
    to support multi-field sorting (e.g., "status asc, created_at desc").
    """

    field: str
    direction: SortDirection = SortDirection.ASC


class FilterOperator(StrEnum):
    """The comparison a :class:`FilterSpec` applies. Deliberately a small,
    generic set — a concrete repository maps these onto its datastore's
    native query mechanism (SQL ``WHERE``, a Cypher predicate, a Qdrant
    filter clause); this contract does not assume SQL.
    """

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """One field-comparison-value filter. A repository call accepts
    ``list[FilterSpec]``, combined with logical AND — matching
    docs/architecture/specification/81_API_Standards.md's Filtering
    section's "Combined Filters" default.
    """

    field: str
    operator: FilterOperator
    value: object
