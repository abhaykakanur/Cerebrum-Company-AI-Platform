"""``DocumentManifestRepository``: the 1:1 manifest record per
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
— CIS Phase 2 Prompt 4's Document Manifest. Mirrors
cerebrum.repositories.postgres.document_metadata_repository.DocumentMetadataRepository's
exact shape.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.document_manifest import (
    DocumentManifest,
)


class DocumentManifestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> DocumentManifest | None:
        return await self._session.get(DocumentManifest, entity_id)

    async def get_by_version(
        self, document_version_id: uuid.UUID
    ) -> DocumentManifest | None:
        result = await self._session.execute(
            select(DocumentManifest).where(
                DocumentManifest.document_version_id == document_version_id
            )
        )
        return result.scalar_one_or_none()

    async def add(self, entity: DocumentManifest) -> DocumentManifest:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: DocumentManifest) -> DocumentManifest:
        await self._session.flush()
        return entity
