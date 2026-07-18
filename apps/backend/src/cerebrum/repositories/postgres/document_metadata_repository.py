"""``DocumentMetadataRepository``: the 1:1 metadata record per
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
— CIS Phase 2 Prompt 1's Metadata Management. No ``list()``/pagination:
metadata is never browsed independently of its owning version, only
fetched by version ID — see
cerebrum.application.knowledge.metadata_service.MetadataService, the
only caller.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
)


class DocumentMetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> DocumentMetadata | None:
        return await self._session.get(DocumentMetadata, entity_id)

    async def get_by_version(
        self, document_version_id: uuid.UUID
    ) -> DocumentMetadata | None:
        result = await self._session.execute(
            select(DocumentMetadata).where(
                DocumentMetadata.document_version_id == document_version_id
            )
        )
        return result.scalar_one_or_none()

    async def add(self, entity: DocumentMetadata) -> DocumentMetadata:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: DocumentMetadata) -> DocumentMetadata:
        await self._session.flush()
        return entity
