# Repository Guide

`cerebrum.repositories` defines the contracts a future concrete
repository implements — no concrete repository exists yet (see this
milestone's Non-Objectives; the first one arrives with Phase 2's
Identity Platform). This guide is for whoever implements that first one.

## The Contracts

| Module | Provides |
|---|---|
| `cerebrum.repositories.base` | `AbstractRepository[EntityT, IDT]` — `get_by_id`, `add`, `update`, `delete`, `list`. |
| `cerebrum.repositories.contracts` | `Pagination`, `Page`, `SortSpec`/`SortDirection`, `FilterSpec`/`FilterOperator` — the shapes `list()` accepts and returns. |
| `cerebrum.repositories.soft_delete` | `SoftDeleteRepository[EntityT, IDT]` — `soft_delete`/`restore`, for entities that must remain queryable after deletion. Implement only if the entity actually needs it. |

All three are framework- and datastore-agnostic: no SQLAlchemy, Neo4j,
or Qdrant import appears in any of them, so the same contract can be
satisfied by a PostgreSQL-backed repository, a Neo4j-backed repository,
or any future adapter.

## Implementing a Concrete Repository

```python
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from sqlalchemy.ext.asyncio import AsyncSession

class SqlAlchemyWidgetRepository(AbstractRepository[Widget, UUID]):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session  # supplied by a UnitOfWork — see transaction-guide.md

    async def get_by_id(self, entity_id: UUID) -> Widget | None:
        return await self._session.get(WidgetModel, entity_id)

    async def add(self, entity: Widget) -> Widget: ...
    async def update(self, entity: Widget) -> Widget: ...
    async def delete(self, entity_id: UUID) -> None: ...

    async def list(
        self, *, pagination: Pagination, filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Widget]:
        # Translate FilterSpec/SortSpec into this datastore's native
        # query mechanism (SQLAlchemy `where`/`order_by` here; a Cypher
        # predicate for a Neo4j-backed repository; a Qdrant filter
        # clause for a vector-backed one) — the contract doesn't assume SQL.
        ...
```

A repository is constructed with a session (or, for Neo4j, a
`Neo4jClientManager.session()`) — never with the client *manager*
itself. The manager owns connection lifecycle; the repository owns query
translation. See [connection-lifecycle.md](connection-lifecycle.md) and
[transaction-guide.md](transaction-guide.md).

## Where a Repository Lives

`domain/<domain>/` defines the port (an interface a repository
satisfies, per Clean Architecture — see
`docs/architecture/specification/34_Architecture_Principles.md`);
`repositories/<datastore>/` (or `infrastructure/`, per
`docs/architecture/dependency-rules.md`'s note that this package is a
navigability-motivated specialization of `infrastructure/`) holds the
concrete adapter. Neither exists yet.

## Pagination, Filtering, Sorting

- `Pagination` is offset-based (`page`, `page_size`) with validation
  (`page >= 1`, `1 <= page_size <= 500`). Cursor pagination — required
  by `docs/architecture/specification/81_API_Standards.md` for large or
  frequently-changing result sets like Search results — is Deferred to
  the first repository that needs it; `Pagination` does not yet define a
  cursor variant.
- `Page[EntityT]` is what `list()` returns: `items`, `total_items`, and
  the `Pagination` that produced it, with `total_pages`/`has_next`/`has_previous`
  computed for you.
- `FilterSpec`/`SortSpec` are combined with logical AND across multiple
  filters, matching `81_API_Standards.md`'s "Combined Filters" default.
  `FilterOperator` is deliberately small and SQL-agnostic (`eq`, `neq`,
  `gt`, `gte`, `lt`, `lte`, `in`, `contains`).

Do not confuse `Page`/`Pagination` (this package's repository-layer
contract) with `cerebrum.api.schemas.envelope.PaginationMeta` (the
HTTP response shape) — an application service adapts one into the
other; `repositories/` never imports from `api/`.
