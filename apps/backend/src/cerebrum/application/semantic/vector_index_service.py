"""``VectorIndexService``: CIS Phase 3 Prompt 2's Semantic Services —
the storage/query facade over
:class:`~cerebrum.repositories.qdrant.vector_repository.VectorRepository`.
:class:`~cerebrum.application.semantic.embedding_service.EmbeddingService`
is this service's one writer; search consumers (
:class:`~cerebrum.application.semantic.hybrid_search_service.HybridSearchService`)
are its readers.
"""

import uuid
from typing import Any

from cerebrum.repositories.qdrant.vector_repository import VectorRepository


class VectorIndexService:
    def __init__(self, *, vector_repository: VectorRepository) -> None:
        self._vectors = vector_repository

    async def ensure_ready(self) -> None:
        await self._vectors.ensure_collection()

    async def upsert(
        self,
        *,
        kind: str,
        source_id: uuid.UUID,
        vector: list[float],
        chunk_id: uuid.UUID | None,
        entity_id: uuid.UUID | None,
        document_id: uuid.UUID,
        document_version_id: uuid.UUID,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        embedding_model: str,
        embedding_version: str,
        metadata: dict[str, Any],
        provenance: dict[str, Any],
    ) -> uuid.UUID:
        return await self._vectors.upsert_point(
            kind=kind,
            source_id=source_id,
            vector=vector,
            chunk_id=chunk_id,
            entity_id=entity_id,
            document_id=document_id,
            document_version_id=document_version_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            metadata=metadata,
            provenance=provenance,
        )

    async def is_current(
        self, *, kind: str, source_id: uuid.UUID, embedding_version: str
    ) -> bool:
        """Incremental Updates: ``True`` when ``source_id`` already has
        a point embedded at ``embedding_version`` — the caller (see
        ``EmbeddingService``) skips re-embedding it unless forced.
        """
        point = await self._vectors.get_point(kind, source_id)
        if point is None:
            return False
        return bool(point["payload"].get("embedding_version") == embedding_version)

    async def get_vector(
        self, *, kind: str, source_id: uuid.UUID
    ) -> list[float] | None:
        """Similar Documents/Chunks/Entities: an already-embedded
        artifact's own vector, to search with directly rather than
        re-embedding a fresh text query.
        """
        point = await self._vectors.get_point(kind, source_id)
        if point is None:
            return None
        vector = point.get("vector")
        return vector if isinstance(vector, list) else None

    async def delete_by_document_version(self, document_version_id: uuid.UUID) -> None:
        await self._vectors.delete_by_document_version(document_version_id)

    async def search(
        self,
        *,
        vector: list[float],
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        return await self._vectors.search(
            vector=vector,
            workspace_id=workspace_id,
            kinds=kinds,
            limit=limit,
            score_threshold=score_threshold,
        )

    async def get_statistics(self, *, workspace_id: uuid.UUID) -> dict[str, int]:
        return await self._vectors.get_statistics(workspace_id)
