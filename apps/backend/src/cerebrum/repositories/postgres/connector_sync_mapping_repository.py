"""``ConnectorSyncMappingRepository``: CRUD and by-external-id lookup
over
:class:`~cerebrum.infrastructure.database.models.connector_sync_mapping.ConnectorSyncMapping`
— CIS Phase 5 Prompt 1's Change Tracking / Delta Detection persistence.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.connector_sync_mapping import (
    ConnectorSyncMapping,
)


class ConnectorSyncMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ConnectorSyncMapping | None:
        return await self._session.get(ConnectorSyncMapping, entity_id)

    async def get_by_external_id(
        self, connector_id: uuid.UUID, external_id: str
    ) -> ConnectorSyncMapping | None:
        statement = select(ConnectorSyncMapping).where(
            ConnectorSyncMapping.connector_id == connector_id,
            ConnectorSyncMapping.external_id == external_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def add(self, entity: ConnectorSyncMapping) -> ConnectorSyncMapping:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: ConnectorSyncMapping) -> ConnectorSyncMapping:
        await self._session.flush()
        return entity

    async def list_by_connector(
        self, connector_id: uuid.UUID
    ) -> list[ConnectorSyncMapping]:
        statement = select(ConnectorSyncMapping).where(
            ConnectorSyncMapping.connector_id == connector_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars())
