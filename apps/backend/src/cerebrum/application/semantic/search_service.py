"""``SearchService``: CIS Phase 3 Prompt 2's OpenSearch integration —
indexes documents/chunks/entities into
:class:`~cerebrum.repositories.opensearch.search_index_repository.SearchIndexRepository`
and provides full-text (BM25) search, filtering, highlighting,
faceting, and autocomplete over them.
"""

import uuid
from datetime import datetime
from typing import Any

from cerebrum.application.semantic.events import SearchIndexUpdatedEvent
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk
from cerebrum.infrastructure.database.models.document import Document
from cerebrum.infrastructure.database.models.entity import Entity
from cerebrum.infrastructure.embeddings.kind import EmbeddingKind
from cerebrum.repositories.opensearch.search_index_repository import (
    SearchIndexRepository,
)


class SearchService:
    def __init__(
        self,
        *,
        search_index_repository: SearchIndexRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._index = search_index_repository
        self._events = event_dispatcher

    async def index_version(
        self,
        *,
        document: Document,
        document_version_id: uuid.UUID,
        chunks: list[Chunk],
        entities: list[Entity],
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> int:
        """Search Indexing — CIS Phase 3 Prompt 2's pipeline stage:
        indexes the document itself, every chunk, and every entity
        sourced from this version, then emits
        :class:`~cerebrum.application.semantic.events.SearchIndexUpdatedEvent`.
        Returns the number of documents indexed.
        """
        await self.index_document(
            document, workspace_id=workspace_id, organization_id=organization_id
        )
        for chunk in chunks:
            await self.index_chunk(
                chunk,
                document=document,
                workspace_id=workspace_id,
                organization_id=organization_id,
            )
        for entity in entities:
            await self.index_entity(
                entity, workspace_id=workspace_id, organization_id=organization_id
            )

        indexed_count = 1 + len(chunks) + len(entities)
        self._events.publish(
            SearchIndexUpdatedEvent(
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                indexed_count=indexed_count,
            )
        )
        return indexed_count

    async def ensure_ready(self) -> None:
        await self._index.ensure_index()

    async def index_document(
        self, document: Document, *, workspace_id: uuid.UUID, organization_id: uuid.UUID
    ) -> None:
        await self._index.index_artifact(
            kind="document",
            source_id=str(document.id),
            workspace_id=str(workspace_id),
            organization_id=str(organization_id),
            document_id=str(document.id),
            document_version_id=None,
            chunk_id=None,
            entity_id=None,
            title=document.name,
            content=document.name,
            tags=[],
            created_at=document.created_at,
        )

    async def index_chunk(
        self,
        chunk: Chunk,
        *,
        document: Document,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> None:
        await self._index.index_artifact(
            kind=EmbeddingKind.CHUNK.value,
            source_id=str(chunk.id),
            workspace_id=str(workspace_id),
            organization_id=str(organization_id),
            document_id=str(document.id),
            document_version_id=str(chunk.document_version_id),
            chunk_id=str(chunk.id),
            entity_id=None,
            title=document.name,
            content=chunk.text,
            tags=[],
            created_at=chunk.created_at,
        )

    async def index_entity(
        self,
        entity: Entity,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> None:
        content = entity.description or entity.canonical_name
        await self._index.index_artifact(
            kind="entity",
            source_id=str(entity.id),
            workspace_id=str(workspace_id),
            organization_id=str(organization_id),
            document_id=str(entity.source_document_id or entity.id),
            document_version_id=None,
            chunk_id=str(entity.source_chunk_id) if entity.source_chunk_id else None,
            entity_id=str(entity.id),
            title=entity.canonical_name,
            content=content,
            tags=[entity.entity_type],
            created_at=entity.created_at,
        )

    async def delete_by_document_version(self, document_version_id: uuid.UUID) -> None:
        await self._index.delete_by_document_version(str(document_version_id))

    async def search(
        self,
        *,
        query_text: str,
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        tags: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await self._index.search(
            query_text=query_text,
            workspace_id=str(workspace_id),
            kinds=kinds,
            tags=tags,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )

    async def search_by_metadata(
        self,
        *,
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        tags: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await self._index.filter_search(
            workspace_id=str(workspace_id),
            kinds=kinds,
            tags=tags,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )

    async def autocomplete(
        self, *, prefix: str, workspace_id: uuid.UUID, limit: int = 10
    ) -> list[str]:
        return await self._index.autocomplete(
            prefix=prefix, workspace_id=str(workspace_id), limit=limit
        )

    async def get_statistics(self, *, workspace_id: uuid.UUID) -> dict[str, int]:
        count = await self._index.count(workspace_id=str(workspace_id))
        return {"indexed_document_count": count}
