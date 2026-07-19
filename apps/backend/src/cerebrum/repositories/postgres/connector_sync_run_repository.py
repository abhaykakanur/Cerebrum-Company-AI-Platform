"""``ConnectorSyncRunRepository``: append-mostly CRUD over
:class:`~cerebrum.infrastructure.database.models.connector_sync_run.ConnectorSyncRun`
— CIS Phase 5 Prompt 1's Observability (sync history, duration, items
processed, failures) and Resume Failed Sync (the latest run's
``cursor``/``status``) requirements.
"""

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.connector_sync_run import (
    ConnectorSyncRun,
    SyncRunStatus,
)
from cerebrum.repositories.contracts import Page, Pagination


class ConnectorSyncRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ConnectorSyncRun | None:
        return await self._session.get(ConnectorSyncRun, entity_id)

    async def add(self, entity: ConnectorSyncRun) -> ConnectorSyncRun:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: ConnectorSyncRun) -> ConnectorSyncRun:
        await self._session.flush()
        return entity

    async def get_latest_for_connector(
        self, connector_id: uuid.UUID
    ) -> ConnectorSyncRun | None:
        statement = (
            select(ConnectorSyncRun)
            .where(ConnectorSyncRun.connector_id == connector_id)
            .order_by(desc(ConnectorSyncRun.started_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_failed_for_connector(
        self, connector_id: uuid.UUID
    ) -> ConnectorSyncRun | None:
        """Resume Failed Sync's lookup — the most recent run that ended
        in :attr:`~SyncRunStatus.FAILED`, whose ``cursor`` (if any)
        tells the next run where to continue from.
        """
        statement = (
            select(ConnectorSyncRun)
            .where(
                ConnectorSyncRun.connector_id == connector_id,
                ConnectorSyncRun.status == SyncRunStatus.FAILED.value,
            )
            .order_by(desc(ConnectorSyncRun.started_at))
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_connector(
        self, connector_id: uuid.UUID, *, pagination: Pagination
    ) -> Page[ConnectorSyncRun]:
        base_statement = select(ConnectorSyncRun).where(
            ConnectorSyncRun.connector_id == connector_id
        )
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_items = (await self._session.execute(count_statement)).scalar_one()

        statement = base_statement.order_by(desc(ConnectorSyncRun.started_at))
        statement = statement.offset(pagination.offset).limit(pagination.page_size)
        items = list((await self._session.execute(statement)).scalars())

        return Page(items=items, total_items=total_items, pagination=pagination)
