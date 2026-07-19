"""``ConnectorRepository``: CRUD, soft delete/restore, and
scheduling-due queries over
:class:`~cerebrum.infrastructure.database.models.connector.Connector`
— CIS Phase 5 Prompt 1's Connector Framework. Mirrors
cerebrum.repositories.postgres.conversation_repository.ConversationRepository's
exact shape.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.connector import (
    Connector,
    ConnectorStatus,
)
from cerebrum.repositories.base import AbstractRepository
from cerebrum.repositories.contracts import FilterSpec, Page, Pagination, SortSpec
from cerebrum.repositories.postgres.query_utils import (
    apply_filters,
    apply_pagination,
    apply_sort,
)
from cerebrum.repositories.soft_delete import SoftDeleteRepository
from cerebrum.utils.clock import utcnow


class ConnectorRepository(
    AbstractRepository[Connector, uuid.UUID], SoftDeleteRepository[Connector, uuid.UUID]
):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Connector | None:
        connector = await self._session.get(Connector, entity_id)
        return None if connector is None or connector.is_deleted else connector

    async def get_by_id_including_deleted(
        self, entity_id: uuid.UUID
    ) -> Connector | None:
        return await self._session.get(Connector, entity_id)

    async def add(self, entity: Connector) -> Connector:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Connector) -> Connector:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        connector = await self._session.get(Connector, entity_id)
        if connector is not None:
            await self._session.delete(connector)
            await self._session.flush()

    async def soft_delete(self, entity_id: uuid.UUID) -> None:
        connector = await self._session.get(Connector, entity_id)
        if connector is not None:
            connector.is_deleted = True
            connector.deleted_at = utcnow()
            await self._session.flush()

    async def restore(self, entity_id: uuid.UUID) -> None:
        connector = await self._session.get(Connector, entity_id)
        if connector is not None:
            connector.is_deleted = False
            connector.deleted_at = None
            await self._session.flush()

    async def list_due_for_sync(self, *, as_of: datetime) -> list[Connector]:
        """Scheduling — CIS Phase 5 Prompt 1's Periodic Sync: every
        active, non-deleted connector whose
        :attr:`~cerebrum.infrastructure.database.models.connector.Connector.next_sync_at`
        has arrived. See cerebrum.application.connectors.scheduler for
        why this is a query a caller polls rather than a timer this
        codebase itself runs.

        Defined before :meth:`list` in this class body deliberately —
        a method named ``list`` shadows the ``list`` builtin for every
        annotation evaluated later in the same class body, so any
        method using a bare ``list[...]`` return type must be defined
        above it.
        """
        statement = select(Connector).where(
            Connector.is_deleted.is_(False),
            Connector.status == ConnectorStatus.ACTIVE.value,
            Connector.sync_interval_seconds.is_not(None),
            Connector.next_sync_at.is_not(None),
            Connector.next_sync_at <= as_of,
        )
        result = await self._session.execute(statement)
        return list(result.scalars())

    async def list(
        self,
        *,
        pagination: Pagination,
        filters: list[FilterSpec] | None = None,
        sort: list[SortSpec] | None = None,
    ) -> Page[Connector]:
        base_statement = apply_filters(select(Connector), Connector, filters).where(
            Connector.is_deleted.is_(False)
        )

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = apply_sort(base_statement, Connector, sort)
        statement = apply_pagination(statement, pagination)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
