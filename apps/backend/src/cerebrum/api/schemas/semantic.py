"""Request/response schemas for CIS Phase 3 Prompt 2's Semantic
Intelligence API. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` (``from_attributes=True``)
so a route can return ``XResponse.model_validate(orm_object)`` directly
— see cerebrum.api.schemas.knowledge's identical docstring precedent.
"""

import uuid
from typing import TYPE_CHECKING, Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel

if TYPE_CHECKING:
    from cerebrum.application.semantic.hybrid_search_service import SearchHit

# --- Citations & search hits --------------------------------------------------


class CitationResponse(APIModel):
    document_id: uuid.UUID | None
    document_version_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    entity_id: uuid.UUID | None
    confidence: float
    provenance: dict[str, Any]


class SearchHitResponse(APIModel):
    source_id: str
    kind: str
    title: str
    snippet: str
    fused_score: float
    vector_score: float | None
    keyword_score: float | None
    citation: CitationResponse

    @classmethod
    def from_hit(cls, hit: "SearchHit") -> "SearchHitResponse":
        return cls(
            source_id=hit.source_id,
            kind=hit.kind,
            title=hit.title,
            snippet=hit.snippet,
            fused_score=hit.fused_score,
            vector_score=hit.vector_score,
            keyword_score=hit.keyword_score,
            citation=CitationResponse(
                document_id=hit.citation.document_id,
                document_version_id=hit.citation.document_version_id,
                chunk_id=hit.citation.chunk_id,
                entity_id=hit.citation.entity_id,
                confidence=hit.citation.confidence,
                provenance=hit.citation.provenance,
            ),
        )


# --- Requests -----------------------------------------------------------------


class RegenerateEmbeddingsRequest(APIModel):
    force: bool = True


# --- Statistics -----------------------------------------------------------------


class SemanticStatisticsResponse(APIModel):
    vector_count: int
    indexed_document_count: int


class EmbeddingJobResponse(APIModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    job_type: str
    status: str
    progress_percent: int
    retry_count: int
    max_retries: int
    error_message: str | None


class ReindexResponse(APIModel):
    indexed_count: int


class AutocompleteResponse(APIModel):
    suggestions: list[str] = Field(default_factory=list)
