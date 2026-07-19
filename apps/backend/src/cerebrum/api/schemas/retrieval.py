"""Request/response schemas for CIS Phase 3 Prompt 3's Retrieval Engine,
Context Builder & Explainability API. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` — see
cerebrum.api.schemas.semantic's identical docstring precedent. Each
``from_x`` classmethod translates the matching application-layer
dataclass, using ``TYPE_CHECKING`` imports to avoid a hard app-layer
import at schema-module load time (same pattern
cerebrum.api.schemas.semantic.SearchHitResponse.from_hit established).
"""

import uuid
from typing import TYPE_CHECKING, Any

from cerebrum.api.schemas.base import APIModel
from cerebrum.api.schemas.semantic import CitationResponse, SearchHitResponse

if TYPE_CHECKING:
    from cerebrum.application.retrieval.citation_service import EnrichedCitation
    from cerebrum.application.retrieval.context_builder_service import ContextPackage
    from cerebrum.application.retrieval.explainability_service import Explanation
    from cerebrum.application.retrieval.ranking_service import (
        RankedResult,
        RankingFactors,
    )

# --- Ranking --------------------------------------------------------------


class RankingFactorsResponse(APIModel):
    hybrid_score: float
    vector_similarity: float
    bm25_score: float
    graph_proximity: float
    entity_importance: float
    recency: float
    source_confidence: float
    document_quality: float

    @classmethod
    def from_factors(cls, factors: "RankingFactors") -> "RankingFactorsResponse":
        return cls(**factors.as_dict())


class RankedResultResponse(APIModel):
    hit: SearchHitResponse
    factors: RankingFactorsResponse
    final_score: float

    @classmethod
    def from_ranked(cls, ranked: "RankedResult") -> "RankedResultResponse":
        return cls(
            hit=SearchHitResponse.from_hit(ranked.hit),
            factors=RankingFactorsResponse.from_factors(ranked.factors),
            final_score=ranked.final_score,
        )


# --- Citations --------------------------------------------------------------


class EnrichedCitationResponse(APIModel):
    document_id: uuid.UUID | None
    document_version_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    entity_id: uuid.UUID | None
    confidence: float
    provenance: dict[str, Any]
    document_name: str | None
    version_number: int | None
    chunk_index: int | None
    entity_name: str | None

    @classmethod
    def from_citation(cls, citation: "EnrichedCitation") -> "EnrichedCitationResponse":
        return cls(
            document_id=citation.document_id,
            document_version_id=citation.document_version_id,
            chunk_id=citation.chunk_id,
            entity_id=citation.entity_id,
            confidence=citation.confidence,
            provenance=citation.provenance,
            document_name=citation.document_name,
            version_number=citation.version_number,
            chunk_index=citation.chunk_index,
            entity_name=citation.entity_name,
        )


# --- Context ------------------------------------------------------------


class ContextDocumentResponse(APIModel):
    document_id: uuid.UUID
    name: str
    version_id: uuid.UUID | None
    version_number: int | None


class ContextChunkResponse(APIModel):
    chunk_id: uuid.UUID
    document_version_id: uuid.UUID
    chunk_index: int
    text: str
    citation: CitationResponse


class ContextEntityResponse(APIModel):
    entity_id: uuid.UUID
    entity_type: str
    canonical_name: str
    description: str | None
    confidence: float
    citation: CitationResponse


class ContextRelationshipResponse(APIModel):
    relationship_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    confidence: float


class VersionHistoryEntryResponse(APIModel):
    document_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    is_current: bool


class ContextPackageResponse(APIModel):
    query_text: str | None
    documents: list[ContextDocumentResponse]
    chunks: list[ContextChunkResponse]
    entities: list[ContextEntityResponse]
    entities_by_type: dict[str, list[ContextEntityResponse]]
    relationships: list[ContextRelationshipResponse]
    graph_neighbors: dict[str, list[dict[str, Any]]]
    version_history: list[VersionHistoryEntryResponse]
    citations: list["EnrichedCitationResponse"]
    truncated: bool

    @classmethod
    def from_package(
        cls,
        package: "ContextPackage",
        *,
        citations: list["EnrichedCitationResponse"],
    ) -> "ContextPackageResponse":
        def _citation(citation: Any) -> CitationResponse:
            return CitationResponse(
                document_id=citation.document_id,
                document_version_id=citation.document_version_id,
                chunk_id=citation.chunk_id,
                entity_id=citation.entity_id,
                confidence=citation.confidence,
                provenance=citation.provenance,
            )

        def _entity(entity: Any) -> ContextEntityResponse:
            return ContextEntityResponse(
                entity_id=entity.entity_id,
                entity_type=entity.entity_type,
                canonical_name=entity.canonical_name,
                description=entity.description,
                confidence=entity.confidence,
                citation=_citation(entity.citation),
            )

        return cls(
            query_text=package.query_text,
            documents=[
                ContextDocumentResponse(
                    document_id=doc.document_id,
                    name=doc.name,
                    version_id=doc.version_id,
                    version_number=doc.version_number,
                )
                for doc in package.documents
            ],
            chunks=[
                ContextChunkResponse(
                    chunk_id=chunk.chunk_id,
                    document_version_id=chunk.document_version_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    citation=_citation(chunk.citation),
                )
                for chunk in package.chunks
            ],
            entities=[_entity(entity) for entity in package.entities],
            entities_by_type={
                entity_type: [_entity(entity) for entity in entities]
                for entity_type, entities in package.entities_by_type.items()
            },
            relationships=[
                ContextRelationshipResponse(
                    relationship_id=rel.relationship_id,
                    source_entity_id=rel.source_entity_id,
                    target_entity_id=rel.target_entity_id,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                )
                for rel in package.relationships
            ],
            graph_neighbors=package.graph_neighbors,
            version_history=[
                VersionHistoryEntryResponse(
                    document_id=entry.document_id,
                    version_id=entry.version_id,
                    version_number=entry.version_number,
                    is_current=entry.is_current,
                )
                for entry in package.version_history
            ],
            citations=citations,
            truncated=package.truncated,
        )


# --- Explainability ---------------------------------------------------------


class ExplanationResponse(APIModel):
    source_id: str
    strategy: str
    why_selected: str
    ranking_factors: RankingFactorsResponse
    supporting_evidence: list[str]
    confidence_breakdown: dict[str, float]
    final_score: float

    @classmethod
    def from_explanation(cls, explanation: "Explanation") -> "ExplanationResponse":
        return cls(
            source_id=explanation.source_id,
            strategy=explanation.strategy,
            why_selected=explanation.why_selected,
            ranking_factors=RankingFactorsResponse.from_factors(
                explanation.ranking_factors
            ),
            supporting_evidence=explanation.supporting_evidence,
            confidence_breakdown=explanation.confidence_breakdown,
            final_score=explanation.final_score,
        )


# --- Statistics ---------------------------------------------------------


class RetrievalStatisticsResponse(APIModel):
    vector_count: int
    indexed_document_count: int
    entity_count: int
    relationship_count: int
