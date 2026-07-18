"""``DocumentExtractionRepository``: the 1:1 extraction-result record per
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
— CIS Phase 2 Prompt 3's Intelligent Document Processing Pipeline.
Mirrors
cerebrum.repositories.postgres.document_metadata_repository.DocumentMetadataRepository's
exact shape: no ``list()``/pagination, fetched only by version ID.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
)


class DocumentExtractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> DocumentExtraction | None:
        return await self._session.get(DocumentExtraction, entity_id)

    async def get_by_version(
        self, document_version_id: uuid.UUID
    ) -> DocumentExtraction | None:
        result = await self._session.execute(
            select(DocumentExtraction).where(
                DocumentExtraction.document_version_id == document_version_id
            )
        )
        return result.scalar_one_or_none()

    async def add(self, entity: DocumentExtraction) -> DocumentExtraction:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: DocumentExtraction) -> DocumentExtraction:
        await self._session.flush()
        return entity
