"""``AbstractRepository``: the CRUD contract every future concrete
repository implements.

Framework- and datastore-agnostic on purpose — no SQLAlchemy, Neo4j, or
Qdrant import appears here — so the same contract can be satisfied by a
PostgreSQL-backed repository, a Neo4j-backed repository, or any other
future adapter without this module changing. See CIS Phase 1 Prompt 4's
"No concrete business repositories" scope: no subclass exists yet.
"""

from abc import ABC, abstractmethod

from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec


class AbstractRepository[EntityT, IDT](ABC):
    """CRUD plus paginated/filtered/sorted listing, generic over the
    entity type ``EntityT`` and its identifier type ``IDT``.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: IDT) -> EntityT | None: ...

    @abstractmethod
    async def add(self, entity: EntityT) -> EntityT: ...

    @abstractmethod
    async def update(self, entity: EntityT) -> EntityT: ...

    @abstractmethod
    async def delete(self, entity_id: IDT) -> None: ...

    @abstractmethod
    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[EntityT]: ...
