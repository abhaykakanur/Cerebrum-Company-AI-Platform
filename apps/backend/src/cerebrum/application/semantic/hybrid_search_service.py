"""``HybridSearchService``: CIS Phase 3 Prompt 2's Hybrid Search —
combines
:class:`~cerebrum.application.semantic.vector_index_service.VectorIndexService`'s
semantic (cosine-similarity) results with
:class:`~cerebrum.application.semantic.search_service.SearchService`'s
keyword (BM25) results via Reciprocal Rank Fusion (RRF) — a standard,
parameter-light rank-fusion technique (no ML, no LLM; see this
milestone's "DO NOT IMPLEMENT: LLM calls"): a hit's fused score is the
sum of ``1 / (k + rank)`` across every ranked list it appears in
(``k=60``, the constant the original RRF paper and most production
hybrid-search systems use), so a document ranked highly by *both*
retrieval methods outranks one only one method liked.

Every hit carries a :class:`Citation` — CIS Phase 3 Prompt 2's Citation
Index requirement — built directly from the payload already stored on
the vector point / search document at index time (see
``EmbeddingService``/``SearchService``), not a second round-trip to
PostgreSQL: source document, document version, chunk reference, entity
reference, confidence, and provenance are already there.

Tenant/workspace isolation is structural, not an afterthought: every
underlying query (vector and keyword) is scoped by ``workspace_id`` —
see ``VectorRepository.search``/``SearchIndexRepository.search``'s own
mandatory workspace filter — so no result from another tenant can ever
reach the fusion step.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from cerebrum.application.semantic.search_service import SearchService
from cerebrum.application.semantic.vector_index_service import VectorIndexService
from cerebrum.infrastructure.embeddings.providers import EmbeddingProvider
from cerebrum.shared.errors.exceptions import NotFoundException

_RRF_K = 60


@dataclass(frozen=True, slots=True)
class Citation:
    document_id: uuid.UUID | None
    document_version_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    entity_id: uuid.UUID | None
    confidence: float
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchHit:
    source_id: str
    kind: str
    title: str
    snippet: str
    fused_score: float
    vector_score: float | None
    keyword_score: float | None
    citation: Citation


class HybridSearchService:
    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        vector_index_service: VectorIndexService,
        search_service: SearchService,
    ) -> None:
        self._provider = provider
        self._vectors = vector_index_service
        self._search = search_service

    async def search(
        self,
        query_text: str,
        *,
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        vector_weight: float = 1.0,
        keyword_weight: float = 1.0,
    ) -> list[SearchHit]:
        candidate_pool = max(limit * 3, limit)
        vector_hits = await self._vector_search(
            query_text, workspace_id=workspace_id, kinds=kinds, limit=candidate_pool
        )
        keyword_hits = await self._keyword_search(
            query_text,
            workspace_id=workspace_id,
            kinds=kinds,
            tags=tags,
            limit=candidate_pool,
        )
        fused = self._fuse(vector_hits, keyword_hits, vector_weight, keyword_weight)
        return fused[:limit]

    async def similar_to_vector(
        self,
        vector: list[float],
        *,
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        limit: int = 10,
        exclude_source_id: uuid.UUID | None = None,
    ) -> list[SearchHit]:
        """Backs Similar Documents/Chunks/Entities: vector-only
        similarity against an already-embedded artifact's own vector,
        rather than a fresh text query.
        """
        raw = await self._vectors.search(
            vector=vector,
            workspace_id=workspace_id,
            kinds=kinds,
            limit=limit + (1 if exclude_source_id else 0),
        )
        hits = [self._hit_from_vector_point(point) for point in raw]
        if exclude_source_id is not None:
            hits = [h for h in hits if h.source_id != str(exclude_source_id)]
        return hits[:limit]

    async def similar_to_source(
        self,
        *,
        kind: str,
        source_id: uuid.UUID,
        workspace_id: uuid.UUID,
        kinds: list[str] | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Similar Documents/Chunks/Entities: looks up ``source_id``'s
        own already-embedded vector (kind ``kind``) and finds other
        artifacts near it — see :meth:`similar_to_vector`. Raises
        :class:`~cerebrum.shared.errors.exceptions.NotFoundException`
        if ``source_id`` has no embedding yet (it hasn't been through
        the pipeline's Embedding Generation stage).
        """
        vector = await self._vectors.get_vector(kind=kind, source_id=source_id)
        if vector is None:
            raise NotFoundException(
                f"No embedding found for {kind} {source_id} — it may not have "
                f"been processed yet."
            )
        return await self.similar_to_vector(
            vector,
            workspace_id=workspace_id,
            kinds=kinds or [kind],
            limit=limit,
            exclude_source_id=source_id,
        )

    async def _vector_search(
        self,
        query_text: str,
        *,
        workspace_id: uuid.UUID,
        kinds: list[str] | None,
        limit: int,
    ) -> list[SearchHit]:
        vector = self._provider.embed([query_text])[0]
        raw = await self._vectors.search(
            vector=vector, workspace_id=workspace_id, kinds=kinds, limit=limit
        )
        return [self._hit_from_vector_point(point) for point in raw]

    async def _keyword_search(
        self,
        query_text: str,
        *,
        workspace_id: uuid.UUID,
        kinds: list[str] | None,
        tags: list[str] | None,
        limit: int,
    ) -> list[SearchHit]:
        response = await self._search.search(
            query_text=query_text,
            workspace_id=workspace_id,
            kinds=kinds,
            tags=tags,
            limit=limit,
        )
        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit["_source"]
            highlight = hit.get("highlight", {})
            snippet_parts = highlight.get("content") or highlight.get("title") or []
            snippet = (
                " ".join(snippet_parts)
                if snippet_parts
                else source.get("content", "")[:200]
            )
            hits.append(
                SearchHit(
                    source_id=source["source_id"],
                    kind=source["kind"],
                    title=source.get("title", ""),
                    snippet=snippet,
                    fused_score=0.0,
                    vector_score=None,
                    keyword_score=hit.get("_score", 0.0),
                    citation=Citation(
                        document_id=_maybe_uuid(source.get("document_id")),
                        document_version_id=_maybe_uuid(
                            source.get("document_version_id")
                        ),
                        chunk_id=_maybe_uuid(source.get("chunk_id")),
                        entity_id=_maybe_uuid(source.get("entity_id")),
                        confidence=min(hit.get("_score", 0.0) / 10.0, 1.0),
                        provenance={"index": "opensearch"},
                    ),
                )
            )
        return hits

    @staticmethod
    def _hit_from_vector_point(point: dict[str, Any]) -> SearchHit:
        payload = point["payload"]
        return SearchHit(
            source_id=payload["source_id"],
            kind=payload["kind"],
            title=payload.get("metadata", {}).get("title", payload["kind"]),
            snippet="",
            fused_score=0.0,
            vector_score=point["score"],
            keyword_score=None,
            citation=Citation(
                document_id=_maybe_uuid(payload.get("document_id")),
                document_version_id=_maybe_uuid(payload.get("document_version_id")),
                chunk_id=_maybe_uuid(payload.get("chunk_id")),
                entity_id=_maybe_uuid(payload.get("entity_id")),
                confidence=point["score"],
                provenance=payload.get("provenance", {}) | {"index": "qdrant"},
            ),
        )

    @staticmethod
    def _fuse(
        vector_hits: list[SearchHit],
        keyword_hits: list[SearchHit],
        vector_weight: float,
        keyword_weight: float,
    ) -> list[SearchHit]:
        scores: dict[str, float] = {}
        by_id: dict[str, SearchHit] = {}

        for rank, hit in enumerate(vector_hits):
            scores[hit.source_id] = scores.get(hit.source_id, 0.0) + vector_weight / (
                _RRF_K + rank + 1
            )
            by_id[hit.source_id] = hit

        for rank, hit in enumerate(keyword_hits):
            scores[hit.source_id] = scores.get(hit.source_id, 0.0) + keyword_weight / (
                _RRF_K + rank + 1
            )
            if hit.source_id in by_id:
                existing = by_id[hit.source_id]
                by_id[hit.source_id] = SearchHit(
                    source_id=existing.source_id,
                    kind=existing.kind,
                    title=existing.title or hit.title,
                    snippet=hit.snippet or existing.snippet,
                    fused_score=0.0,
                    vector_score=existing.vector_score,
                    keyword_score=hit.keyword_score,
                    citation=existing.citation,
                )
            else:
                by_id[hit.source_id] = hit

        ranked_ids = sorted(
            scores, key=lambda source_id: scores[source_id], reverse=True
        )
        results = []
        for source_id in ranked_ids:
            hit = by_id[source_id]
            results.append(
                SearchHit(
                    source_id=hit.source_id,
                    kind=hit.kind,
                    title=hit.title,
                    snippet=hit.snippet,
                    fused_score=scores[source_id],
                    vector_score=hit.vector_score,
                    keyword_score=hit.keyword_score,
                    citation=hit.citation,
                )
            )
        return results


def _maybe_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None
