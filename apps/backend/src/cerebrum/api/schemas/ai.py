"""Request/response schemas for CIS Phase 4 Prompt 1's Enterprise RAG
Engine API. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` — see
cerebrum.api.schemas.semantic's identical docstring precedent. Reuses
:class:`~cerebrum.api.schemas.retrieval.EnrichedCitationResponse` for
citations rather than redefining it, since CIS Phase 4 Prompt 1's
Citation Support is built directly on CIS Phase 3 Prompt 3's Citation
Engine — the same object, not a parallel one.
"""

from typing import TYPE_CHECKING, Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel
from cerebrum.api.schemas.retrieval import EnrichedCitationResponse
from cerebrum.application.retrieval.retrieval_service import RetrievalStrategy

if TYPE_CHECKING:
    from cerebrum.application.ai.ai_response_service import RAGAnswer

# --- Requests -----------------------------------------------------------------


class AskRequest(APIModel):
    question: str = Field(min_length=1)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    limit: int = Field(default=10, ge=1, le=50)
    max_context_tokens: int = Field(default=3000, ge=1)
    max_tokens: int = Field(default=1024, ge=1, le=32_000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    model: str | None = None


class CitationsRequest(APIModel):
    question: str = Field(min_length=1)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    limit: int = Field(default=10, ge=1, le=50)


# --- Responses ------------------------------------------------------------


class ConfidenceBreakdownResponse(APIModel):
    retrieval_confidence: float
    citation_coverage: float
    context_completeness: float
    source_diversity: float
    overall: float


class RAGAnswerResponse(APIModel):
    answer: str
    citations: list[EnrichedCitationResponse]
    confidence: ConfidenceBreakdownResponse
    strategy: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    context_truncated: bool

    @classmethod
    def from_answer(cls, answer: "RAGAnswer") -> "RAGAnswerResponse":
        return cls(
            answer=answer.answer,
            citations=[
                EnrichedCitationResponse.from_citation(c) for c in answer.citations
            ],
            confidence=ConfidenceBreakdownResponse(
                retrieval_confidence=answer.confidence.retrieval_confidence,
                citation_coverage=answer.confidence.citation_coverage,
                context_completeness=answer.confidence.context_completeness,
                source_diversity=answer.confidence.source_diversity,
                overall=answer.confidence.overall,
            ),
            strategy=answer.strategy,
            provider=answer.provider,
            model=answer.model,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
            context_truncated=answer.context_truncated,
        )


class AIProviderConfigResponse(APIModel):
    available_providers: list[str]
    default_provider: str
    default_temperature: float
    default_max_tokens: int
    default_max_context_tokens: int
    default_model_by_provider: dict[str, str]


class AIUsageStatisticsResponse(APIModel):
    question_count: int
    prompt_tokens: int
    completion_tokens: int
    providers: dict[str, int]

    @classmethod
    def from_stats(cls, stats: dict[str, Any]) -> "AIUsageStatisticsResponse":
        return cls(
            question_count=stats["question_count"],
            prompt_tokens=stats["prompt_tokens"],
            completion_tokens=stats["completion_tokens"],
            providers=stats["providers"],
        )
