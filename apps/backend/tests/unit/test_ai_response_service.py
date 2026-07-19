"""Proves CIS Phase 4 Prompt 1's ``AIResponseService``: Citation
Verification (only marker-referenced citations are attached, with a
fallback to every offered citation when none are referenced) and the
four-factor Confidence computation, plus ``AIResponseGeneratedEvent``
publication.
"""

import uuid

import pytest

from cerebrum.application.ai.ai_response_service import AIResponseService
from cerebrum.application.ai.events import AIResponseGeneratedEvent
from cerebrum.application.ai.prompt_builder_service import BuiltPrompt
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.application.retrieval.context_builder_service import (
    ContextChunk,
    ContextEntity,
    ContextPackage,
)
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalResult,
    RetrievalStrategy,
)
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.llm.provider import LLMMessage, LLMResponse, LLMUsage

pytestmark = pytest.mark.unit


def _hit(source_id: str, *, confidence: float = 0.8) -> SearchHit:
    return SearchHit(
        source_id=source_id,
        kind="chunk",
        title="Title",
        snippet="",
        fused_score=0.5,
        vector_score=0.5,
        keyword_score=None,
        citation=Citation(
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            entity_id=None,
            confidence=confidence,
            provenance={},
        ),
    )


def _enriched_citation(document_id: uuid.UUID | None = None) -> EnrichedCitation:
    return EnrichedCitation(
        document_id=document_id or uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        entity_id=None,
        confidence=0.9,
        provenance={},
        document_name="Report.pdf",
        version_number=1,
        chunk_index=0,
        entity_name=None,
    )


def _prompt(citation_markers: dict[str, EnrichedCitation]) -> BuiltPrompt:
    return BuiltPrompt(
        system_message=LLMMessage(role="system", content="system"),
        user_message=LLMMessage(role="user", content="user"),
        citation_markers=citation_markers,
        estimated_tokens=100,
        truncated=False,
    )


def _llm_response(content: str = "The answer is [1].") -> LLMResponse:
    return LLMResponse(
        content=content,
        model="local-extractive-v1",
        provider="local",
        usage=LLMUsage(prompt_tokens=50, completion_tokens=10),
        finish_reason="stop",
    )


def _retrieval_result(hits: list[SearchHit]) -> RetrievalResult:
    return RetrievalResult(hits=hits, strategy=RetrievalStrategy.HYBRID, query_text="q")


def _context(chunk_count: int = 1, entity_count: int = 0) -> ContextPackage:
    chunks = [
        ContextChunk(
            chunk_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            chunk_index=i,
            text="text",
            citation=Citation(
                document_id=None,
                document_version_id=None,
                chunk_id=None,
                entity_id=None,
                confidence=0.5,
                provenance={},
            ),
        )
        for i in range(chunk_count)
    ]
    entities = [
        ContextEntity(
            entity_id=uuid.uuid4(),
            entity_type="organization",
            canonical_name="Acme",
            description=None,
            confidence=0.5,
            citation=Citation(
                document_id=None,
                document_version_id=None,
                chunk_id=None,
                entity_id=None,
                confidence=0.5,
                provenance={},
            ),
        )
        for _ in range(entity_count)
    ]
    return ContextPackage(
        query_text="q",
        documents=[],
        chunks=chunks,
        entities=entities,
        entities_by_type={},
        relationships=[],
        graph_neighbors={},
        version_history=[],
        citations=[],
        truncated=False,
    )


def test_verify_citations_keeps_only_referenced_markers() -> None:
    cited = _enriched_citation()
    uncited = _enriched_citation()
    markers = {"[1]": cited, "[2]": uncited}
    service = AIResponseService(event_dispatcher=EventDispatcher())

    answer = service.build_answer(
        llm_response=_llm_response("The answer references [1] only."),
        prompt=_prompt(markers),
        retrieval_result=_retrieval_result([_hit("a"), _hit("b")]),
        context=_context(chunk_count=2),
        requested_limit=2,
        workspace_id=uuid.uuid4(),
    )

    assert answer.citations == [cited]


def test_verify_citations_falls_back_to_all_when_none_referenced() -> None:
    first = _enriched_citation()
    second = _enriched_citation()
    markers = {"[1]": first, "[2]": second}
    service = AIResponseService(event_dispatcher=EventDispatcher())

    answer = service.build_answer(
        llm_response=_llm_response("An answer citing nothing explicitly."),
        prompt=_prompt(markers),
        retrieval_result=_retrieval_result([_hit("a")]),
        context=_context(),
        requested_limit=1,
        workspace_id=uuid.uuid4(),
    )

    assert answer.citations == [first, second]


def test_confidence_retrieval_confidence_is_mean_hit_confidence() -> None:
    service = AIResponseService(event_dispatcher=EventDispatcher())
    hits = [_hit("a", confidence=0.4), _hit("b", confidence=0.8)]
    markers = {"[1]": _enriched_citation()}

    answer = service.build_answer(
        llm_response=_llm_response("cites [1]"),
        prompt=_prompt(markers),
        retrieval_result=_retrieval_result(hits),
        context=_context(chunk_count=2),
        requested_limit=2,
        workspace_id=uuid.uuid4(),
    )

    assert answer.confidence.retrieval_confidence == pytest.approx(0.6)


def test_confidence_zero_hits_does_not_divide_by_zero() -> None:
    service = AIResponseService(event_dispatcher=EventDispatcher())

    answer = service.build_answer(
        llm_response=_llm_response("no sources"),
        prompt=_prompt({}),
        retrieval_result=_retrieval_result([]),
        context=_context(chunk_count=0),
        requested_limit=5,
        workspace_id=uuid.uuid4(),
    )

    assert answer.confidence.retrieval_confidence == 0.0
    assert answer.confidence.citation_coverage == 0.0
    assert answer.confidence.source_diversity == 0.0


def test_confidence_context_completeness_reflects_requested_limit() -> None:
    service = AIResponseService(event_dispatcher=EventDispatcher())
    markers = {"[1]": _enriched_citation()}

    answer = service.build_answer(
        llm_response=_llm_response("cites [1]"),
        prompt=_prompt(markers),
        retrieval_result=_retrieval_result([_hit("a")]),
        context=_context(chunk_count=2, entity_count=1),
        requested_limit=10,
        workspace_id=uuid.uuid4(),
    )

    assert answer.confidence.context_completeness == pytest.approx(0.3)


def test_confidence_source_diversity_counts_distinct_documents() -> None:
    service = AIResponseService(event_dispatcher=EventDispatcher())
    same_document = uuid.uuid4()
    citation_a = _enriched_citation(document_id=same_document)
    citation_b = _enriched_citation(document_id=same_document)
    markers = {"[1]": citation_a, "[2]": citation_b}

    answer = service.build_answer(
        llm_response=_llm_response("cites [1] and [2]"),
        prompt=_prompt(markers),
        retrieval_result=_retrieval_result([_hit("a"), _hit("b")]),
        context=_context(chunk_count=2),
        requested_limit=2,
        workspace_id=uuid.uuid4(),
    )

    assert answer.confidence.source_diversity == pytest.approx(0.5)


def test_build_answer_publishes_event() -> None:
    events = EventDispatcher()
    received: list[AIResponseGeneratedEvent] = []
    events.subscribe(AIResponseGeneratedEvent, received.append)
    service = AIResponseService(event_dispatcher=events)
    workspace_id = uuid.uuid4()
    markers = {"[1]": _enriched_citation()}

    service.build_answer(
        llm_response=_llm_response("cites [1]"),
        prompt=_prompt(markers),
        retrieval_result=_retrieval_result([_hit("a")]),
        context=_context(),
        requested_limit=1,
        workspace_id=workspace_id,
    )

    assert len(received) == 1
    assert received[0].workspace_id == workspace_id
    assert received[0].provider == "local"
    assert received[0].citation_count == 1
