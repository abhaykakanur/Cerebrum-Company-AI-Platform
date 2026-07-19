"""``AIResponseService``: CIS Phase 4 Prompt 1's Citation Verification
(Safety) and Confidence computation, and the place a raw
:class:`~cerebrum.infrastructure.llm.provider.LLMResponse` becomes a
citation-backed :class:`RAGAnswer`.

**Citation Verification** (:meth:`_verify_citations`): a citation is
only attached to the final answer if the model's own response text
contains its bracketed marker (e.g. ``[1]``) — a citation the pipeline
retrieved but the model never referenced is dropped, and there is no
path by which a marker/source the model merely invents gets attached,
since the only citations ever considered come from
cerebrum.application.ai.prompt_builder_service.BuiltPrompt.citation_markers
(built from real retrieval results, before the model ever runs). If the
model referenced none of the offered markers (e.g. it answered from
general phrasing without citing), every offered citation is attached
instead — an uncited answer should not silently claim zero sources when
sources were, in fact, retrieved and available.

**Confidence** (:meth:`_compute_confidence`) is a plain average of four
independently-computed signals, all derived from data this pipeline
already has (no additional model call): retrieval confidence (mean
per-hit confidence), citation coverage (fraction of retrieved hits that
ended up cited), context completeness (how much of the requested
retrieval limit was actually resolved into context), and source
diversity (distinct source documents among the cited sources).
"""

import uuid
from dataclasses import dataclass, field

from cerebrum.application.ai.events import AIResponseGeneratedEvent
from cerebrum.application.ai.prompt_builder_service import BuiltPrompt
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.application.retrieval.context_builder_service import ContextPackage
from cerebrum.application.retrieval.retrieval_service import RetrievalResult
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.llm.provider import LLMResponse


@dataclass(frozen=True, slots=True)
class ConfidenceBreakdown:
    retrieval_confidence: float
    citation_coverage: float
    context_completeness: float
    source_diversity: float
    overall: float


@dataclass(frozen=True, slots=True)
class RAGAnswer:
    answer: str
    citations: list[EnrichedCitation]
    confidence: ConfidenceBreakdown
    strategy: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    context_truncated: bool
    all_retrieved_citations: list[EnrichedCitation] = field(default_factory=list)
    """Every citation the pipeline actually offered the model (before
    Citation Verification narrowed ``citations`` down to what the
    model's answer text referenced) — CIS Phase 4 Prompt 2's "Retrieved
    context references" Message field reads this, since it needs the
    full retrieval-result reference set, not just what ended up shown
    to the user. Distinct from ``citations`` on purpose: a follow-up
    turn's retrieval-aware memory should be able to see everything this
    turn considered, even a source the model's answer didn't end up
    citing.
    """


class AIResponseService:
    def __init__(self, *, event_dispatcher: EventDispatcher) -> None:
        self._events = event_dispatcher

    def build_answer(
        self,
        *,
        llm_response: LLMResponse,
        prompt: BuiltPrompt,
        retrieval_result: RetrievalResult,
        context: ContextPackage,
        requested_limit: int,
        workspace_id: uuid.UUID,
    ) -> RAGAnswer:
        verified_citations = self._verify_citations(
            llm_response.content, prompt.citation_markers
        )
        confidence = self._compute_confidence(
            retrieval_result=retrieval_result,
            context=context,
            citations=verified_citations,
            requested_limit=requested_limit,
        )
        answer = RAGAnswer(
            answer=llm_response.content,
            citations=verified_citations,
            confidence=confidence,
            strategy=retrieval_result.strategy.value,
            provider=llm_response.provider,
            model=llm_response.model,
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
            context_truncated=prompt.truncated,
            all_retrieved_citations=list(prompt.citation_markers.values()),
        )
        self._events.publish(
            AIResponseGeneratedEvent(
                workspace_id=workspace_id,
                provider=llm_response.provider,
                model=llm_response.model,
                citation_count=len(verified_citations),
                overall_confidence=confidence.overall,
            )
        )
        return answer

    @staticmethod
    def _verify_citations(
        answer_text: str, citation_markers: dict[str, EnrichedCitation]
    ) -> list[EnrichedCitation]:
        referenced = [
            citation
            for marker, citation in citation_markers.items()
            if marker in answer_text
        ]
        return referenced or list(citation_markers.values())

    @staticmethod
    def _compute_confidence(
        *,
        retrieval_result: RetrievalResult,
        context: ContextPackage,
        citations: list[EnrichedCitation],
        requested_limit: int,
    ) -> ConfidenceBreakdown:
        hits = retrieval_result.hits
        retrieval_confidence = (
            sum(hit.citation.confidence for hit in hits) / len(hits) if hits else 0.0
        )
        citation_coverage = min(len(citations) / max(len(hits), 1), 1.0)

        resolved_count = len(context.chunks) + len(context.entities)
        context_completeness = min(resolved_count / max(requested_limit, 1), 1.0)

        distinct_documents = {
            citation.document_id for citation in citations if citation.document_id
        }
        source_diversity = (
            min(len(distinct_documents) / max(len(citations), 1), 1.0)
            if citations
            else 0.0
        )

        overall = (
            retrieval_confidence
            + citation_coverage
            + context_completeness
            + source_diversity
        ) / 4
        return ConfidenceBreakdown(
            retrieval_confidence=retrieval_confidence,
            citation_coverage=citation_coverage,
            context_completeness=context_completeness,
            source_diversity=source_diversity,
            overall=overall,
        )
