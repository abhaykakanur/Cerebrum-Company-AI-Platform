"""``VectorRepository``: Qdrant-backed embedding storage — CIS Phase 3
Prompt 2's Embedding Storage. One collection
(:data:`_COLLECTION_NAME`) holds every embeddable artifact kind
(chunk/entity description/relationship description/document summary/
metadata), distinguished by a ``kind`` payload field — not one
collection per kind, since every kind shares the same vector
dimensionality (one
:class:`~cerebrum.infrastructure.embeddings.providers.EmbeddingProvider`
per deployment) and payload shape, and a single collection makes
cross-kind similarity search (e.g. "find chunks *and* entities similar
to this query") one query rather than a fan-out across collections.

Every point's ID is deterministic —
``uuid.uuid5(_POINT_NAMESPACE, f"{kind}:{source_id}")`` — so
re-embedding the same source under the same kind overwrites its
existing point (Qdrant's ``upsert`` is itself idempotent by ID) rather
than accumulating duplicates, the same "write is idempotent by
deterministic ID" convention
cerebrum.repositories.neo4j.knowledge_graph_repository.KnowledgeGraphRepository's
``MERGE``-by-``id`` already established for Neo4j.
"""

import uuid
from typing import Any, cast

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

_COLLECTION_NAME = "cerebrum_embeddings"
_POINT_NAMESPACE = uuid.UUID("6f6a1b2c-6e1a-4b7a-9c1e-6a2f7e5d9b10")


def point_id_for(kind: str, source_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(_POINT_NAMESPACE, f"{kind}:{source_id}")


class VectorRepository:
    def __init__(self, client: AsyncQdrantClient, *, vector_size: int) -> None:
        self._client = client
        self._vector_size = vector_size

    async def ensure_collection(self) -> None:
        if not await self._client.collection_exists(_COLLECTION_NAME):
            await self._client.create_collection(
                collection_name=_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=Distance.COSINE
                ),
            )

    async def upsert_point(
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
        point_id = point_id_for(kind, source_id)
        await self._client.upsert(
            collection_name=_COLLECTION_NAME,
            points=[
                PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload={
                        "kind": kind,
                        "source_id": str(source_id),
                        "chunk_id": str(chunk_id) if chunk_id else None,
                        "entity_id": str(entity_id) if entity_id else None,
                        "document_id": str(document_id),
                        "document_version_id": str(document_version_id),
                        "workspace_id": str(workspace_id),
                        "organization_id": str(organization_id),
                        "embedding_model": embedding_model,
                        "embedding_version": embedding_version,
                        "metadata": metadata,
                        "provenance": provenance,
                    },
                )
            ],
        )
        return point_id

    async def get_point(self, kind: str, source_id: uuid.UUID) -> dict[str, Any] | None:
        """Backs Incremental Updates (a caller checks whether a source
        already has a point at the target ``embedding_version`` before
        re-embedding it) and Similar Documents/Chunks/Entities (a
        caller reads an already-embedded artifact's own vector to
        search with, rather than a fresh text query).
        """
        point_id = point_id_for(kind, source_id)
        results = await self._client.retrieve(
            collection_name=_COLLECTION_NAME,
            ids=[str(point_id)],
            with_payload=True,
            with_vectors=True,
        )
        if not results:
            return None
        return {
            "id": results[0].id,
            "payload": results[0].payload,
            "vector": results[0].vector,
        }

    async def delete_by_document_version(self, document_version_id: uuid.UUID) -> None:
        await self._client.delete(
            collection_name=_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_version_id",
                        match=MatchValue(value=str(document_version_id)),
                    )
                ]
            ),
        )

    async def search(
        self,
        *,
        vector: list[float],
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        query_filter = Filter(
            must=cast(
                Any,
                [
                    FieldCondition(
                        key="workspace_id", match=MatchValue(value=str(workspace_id))
                    )
                ],
            ),
            should=cast(Any, self._kind_conditions(kinds)),
        )
        response = await self._client.query_points(
            collection_name=_COLLECTION_NAME,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            {"id": point.id, "score": point.score, "payload": point.payload}
            for point in response.points
        ]

    async def get_statistics(self, workspace_id: uuid.UUID) -> dict[str, int]:
        result = await self._client.count(
            collection_name=_COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="workspace_id", match=MatchValue(value=str(workspace_id))
                    )
                ]
            ),
        )
        return {"vector_count": result.count}

    @staticmethod
    def _kind_conditions(kinds: list[str] | None) -> list[FieldCondition] | None:
        if not kinds:
            return None
        return [FieldCondition(key="kind", match=MatchValue(value=k)) for k in kinds]
