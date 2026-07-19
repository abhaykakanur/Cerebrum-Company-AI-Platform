"""Proves CIS Phase 4 Prompt 1's ``RAGService`` orchestration:
Retrieval Orchestration -> Context Assembly -> Prompt Generation -> LLM
Invocation -> Response Generation -> Citation Attachment for
:meth:`ask`, the same pipeline plus progress/token/completed events and
mid-stream Cancellation for :meth:`ask_stream`.

CIS Phase 3's Retrieval Engine/Context Builder/Citation Engine
(``RetrievalService``/``ContextBuilderService``/``CitationService``)
are faked at their own service-level interface — matching
apps/backend/tests/unit/test_knowledge_preparation_service.py's
"fake the collaborator services this orchestrator composes, not their
own PostgreSQL/Qdrant/Neo4j internals" precedent, since this file's
subject is ``RAGService``'s call order and event publication, not
retrieval correctness (already proven in
apps/backend/tests/unit/test_retrieval_service.py etc.).
``PromptBuilderService``/``AIResponseService`` are the real classes
(pure, deterministic, no I/O), and
:class:`~cerebrum.infrastructure.llm.local_provider.LocalProvider` is
the real dependency-free provider — together giving genuine end-to-end
coverage of everything after retrieval, which is exactly what CIS Phase
4 Prompt 1's "RAG pipeline works end-to-end" acceptance criterion asks
for.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest

from cerebrum.application.ai.ai_response_service import AIResponseService
from cerebrum.application.ai.events import ResponseCompletedEvent
from cerebrum.application.ai.prompt_builder_service import PromptBuilderService
from cerebrum.application.ai.rag_service import (
    CancelledEvent,
    CompletedEvent,
    ErrorEvent,
    ProgressEvent,
    RAGService,
    TokenEvent,
)
from cerebrum.application.ai.usage_stats_service import AIUsageStatsService
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.application.retrieval.context_builder_service import (
    ContextChunk,
    ContextPackage,
)
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalResult,
    RetrievalStrategy,
)
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.llm.local_provider import LocalProvider
from cerebrum.infrastructure.llm.provider import LLMMessage, LLMProviderError
from cerebrum.shared.errors.exceptions import InfrastructureException

pytestmark = pytest.mark.unit


def _hit() -> SearchHit:
    chunk_id = uuid.uuid4()
    return SearchHit(
        source_id=str(chunk_id),
        kind="chunk",
        title="Report",
        snippet="Acme Corp makes widgets.",
        fused_score=0.5,
        vector_score=0.5,
        keyword_score=None,
        citation=Citation(
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            chunk_id=chunk_id,
            entity_id=None,
            confidence=0.9,
            provenance={},
        ),
    )


def _package_for(hit: SearchHit) -> ContextPackage:
    chunk = ContextChunk(
        chunk_id=hit.citation.chunk_id,
        document_version_id=hit.citation.document_version_id,
        chunk_index=0,
        text="Acme Corp makes widgets.",
        citation=hit.citation,
    )
    return ContextPackage(
        query_text="What does Acme Corp make?",
        documents=[],
        chunks=[chunk],
        entities=[],
        entities_by_type={},
        relationships=[],
        graph_neighbors={},
        version_history=[],
        citations=[],
        truncated=False,
    )


def _citation_for(hit: SearchHit) -> EnrichedCitation:
    return EnrichedCitation(
        document_id=hit.citation.document_id,
        document_version_id=hit.citation.document_version_id,
        chunk_id=hit.citation.chunk_id,
        entity_id=None,
        confidence=hit.citation.confidence,
        provenance={},
        document_name="Report.pdf",
        version_number=1,
        chunk_index=0,
        entity_name=None,
    )


class _FakeRetrievalService:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls: list[dict] = []

    async def retrieve(
        self,
        question: str | None = None,
        *,
        workspace_id: uuid.UUID,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        **kwargs: object,
    ) -> RetrievalResult:
        self.calls.append({"question": question, "strategy": strategy, **kwargs})
        return RetrievalResult(hits=self.hits, strategy=strategy, query_text=question)


class _FakeContextBuilderService:
    def __init__(self, package: ContextPackage) -> None:
        self.package = package
        self.calls: list[dict] = []

    async def build(
        self, hits: list[SearchHit], *, workspace_id: uuid.UUID, **kwargs: object
    ) -> ContextPackage:
        self.calls.append(kwargs)
        return self.package


class _FakeCitationService:
    def __init__(self, citations: list[EnrichedCitation]) -> None:
        self.citations = citations

    async def build_citations(
        self, hits: list[SearchHit], *, workspace_id: uuid.UUID
    ) -> list[EnrichedCitation]:
        return self.citations


class _FakeRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[bytes, bytes]] = {}

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        hash_ = self._hashes.setdefault(key, {})
        updated = int(hash_.get(field.encode(), b"0")) + amount
        hash_[field.encode()] = str(updated).encode()
        return updated

    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        return self._hashes.get(key, {})


class _FailingProvider:
    name = "failing"
    default_model = "failing-model"

    async def generate(self, messages: list[LLMMessage], **kwargs: object) -> None:
        raise LLMProviderError("provider unreachable")

    async def stream(
        self, messages: list[LLMMessage], **kwargs: object
    ) -> AsyncGenerator[str, None]:
        raise LLMProviderError("provider unreachable")
        yield ""  # pragma: no cover - makes this a generator function


class _ControllableProvider:
    """Yields tokens on demand — lets a test observe an in-flight
    stream and then cancel it, proving CIS Phase 4 Prompt 1's
    Cancellation requirement actually stops token consumption rather
    than merely being accepted and ignored.
    """

    name = "controllable"
    default_model = "controllable-model"

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self.tokens_yielded = 0

    async def generate(self, messages: list[LLMMessage], **kwargs: object) -> None:
        raise NotImplementedError

    async def stream(
        self, messages: list[LLMMessage], **kwargs: object
    ) -> AsyncGenerator[str, None]:
        for token in self._tokens:
            self.tokens_yielded += 1
            yield token
            await asyncio.sleep(0)


def _rag_service(
    *,
    hits: list[SearchHit] | None = None,
    package: ContextPackage | None = None,
    citations: list[EnrichedCitation] | None = None,
    events: EventDispatcher | None = None,
    redis: _FakeRedis | None = None,
) -> tuple[RAGService, _FakeRetrievalService, _FakeContextBuilderService]:
    hit = hits[0] if hits else _hit()
    events = events or EventDispatcher()
    retrieval = _FakeRetrievalService(hits or [hit])
    context_builder = _FakeContextBuilderService(package or _package_for(hit))
    citation_service = _FakeCitationService(
        citations if citations is not None else [_citation_for(hit)]
    )
    service = RAGService(
        retrieval_service=retrieval,  # type: ignore[arg-type]
        context_builder_service=context_builder,  # type: ignore[arg-type]
        citation_service=citation_service,  # type: ignore[arg-type]
        prompt_builder_service=PromptBuilderService(event_dispatcher=events),
        response_service=AIResponseService(event_dispatcher=events),
        usage_stats_service=AIUsageStatsService(redis=redis or _FakeRedis()),  # type: ignore[arg-type]
        event_dispatcher=events,
    )
    return service, retrieval, context_builder


async def test_ask_end_to_end_with_local_provider() -> None:
    service, retrieval, context_builder = _rag_service()
    workspace_id = uuid.uuid4()

    answer = await service.ask(
        "What does Acme Corp make?",
        workspace_id=workspace_id,
        provider=LocalProvider(),
    )

    assert "widgets" in answer.answer
    assert answer.provider == "local"
    assert len(answer.citations) == 1
    assert answer.confidence.overall > 0
    assert retrieval.calls[0]["question"] == "What does Acme Corp make?"
    assert context_builder.calls[0]["query_text"] == "What does Acme Corp make?"


async def test_ask_publishes_response_completed_event() -> None:
    events = EventDispatcher()
    received: list[ResponseCompletedEvent] = []
    events.subscribe(ResponseCompletedEvent, received.append)
    service, _retrieval, _context_builder = _rag_service(events=events)
    workspace_id = uuid.uuid4()

    await service.ask("q", workspace_id=workspace_id, provider=LocalProvider())

    assert len(received) == 1
    assert received[0].workspace_id == workspace_id
    assert received[0].streamed is False


async def test_ask_records_usage_stats() -> None:
    redis = _FakeRedis()
    service, _retrieval, _context_builder = _rag_service(redis=redis)
    workspace_id = uuid.uuid4()
    usage_stats = AIUsageStatsService(redis=redis)  # type: ignore[arg-type]

    await service.ask("q", workspace_id=workspace_id, provider=LocalProvider())

    stats = await usage_stats.get_statistics(workspace_id=workspace_id)
    assert stats["question_count"] == 1
    assert stats["providers"] == {"local": 1}


async def test_ask_wraps_provider_errors_as_infrastructure_exception() -> None:
    service, _retrieval, _context_builder = _rag_service()

    with pytest.raises(InfrastructureException):
        await service.ask(
            "q", workspace_id=uuid.uuid4(), provider=_FailingProvider()  # type: ignore[arg-type]
        )


async def test_ask_stream_yields_progress_tokens_then_completed() -> None:
    service, _retrieval, _context_builder = _rag_service()
    provider = _ControllableProvider(["Hello", " world"])

    events = [
        event
        async for event in service.ask_stream(
            "q", workspace_id=uuid.uuid4(), provider=provider  # type: ignore[arg-type]
        )
    ]

    stages = [e.stage for e in events if isinstance(e, ProgressEvent)]
    assert stages == ["retrieving", "building_context", "building_prompt", "generating"]
    tokens = [e.token for e in events if isinstance(e, TokenEvent)]
    assert tokens == ["Hello", " world"]
    assert isinstance(events[-1], CompletedEvent)
    assert events[-1].answer.answer == "Hello world"


async def test_ask_stream_yields_error_event_on_provider_failure() -> None:
    service, _retrieval, _context_builder = _rag_service()

    events = [
        event
        async for event in service.ask_stream(
            "q", workspace_id=uuid.uuid4(), provider=_FailingProvider()  # type: ignore[arg-type]
        )
    ]

    assert isinstance(events[-1], ErrorEvent)


async def test_ask_stream_cancellation_stops_token_consumption() -> None:
    service, _retrieval, _context_builder = _rag_service()
    provider = _ControllableProvider(["a", "b", "c", "d", "e"])
    cancellation = asyncio.Event()

    stream = service.ask_stream(
        "q", workspace_id=uuid.uuid4(), provider=provider, cancellation=cancellation  # type: ignore[arg-type]
    )

    seen = []
    async for event in stream:
        seen.append(event)
        if isinstance(event, TokenEvent):
            cancellation.set()
            break

    remaining = [event async for event in stream]

    assert any(isinstance(e, TokenEvent) for e in seen)
    assert len(remaining) == 1
    assert isinstance(remaining[0], CancelledEvent)
    assert provider.tokens_yielded < len(provider._tokens)
