"""``ChunkRepository``: CRUD over
:class:`~cerebrum.infrastructure.database.models.chunk.Chunk` — CIS
Phase 2 Prompt 4's Chunking Engine persistence. Many rows per version,
unlike the 1:1 metadata/extraction repositories — see
:meth:`list_by_document_version`/:meth:`delete_by_document_version`.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.chunk import Chunk


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Chunk | None:
        return await self._session.get(Chunk, entity_id)

    async def list_by_document_version(
        self, document_version_id: uuid.UUID
    ) -> list[Chunk]:
        result = await self._session.execute(
            select(Chunk)
            .where(Chunk.document_version_id == document_version_id)
            .order_by(Chunk.chunk_index)
        )
        return list(result.scalars())

    async def delete_by_document_version(self, document_version_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(Chunk).where(Chunk.document_version_id == document_version_id)
        )
        await self._session.flush()

    async def add(self, entity: Chunk) -> Chunk:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Chunk) -> Chunk:
        await self._session.flush()
        return entity
