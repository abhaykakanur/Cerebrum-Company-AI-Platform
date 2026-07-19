"""Proves CIS Phase 3 Prompt 3's ``RetrievalService``: each of the five
strategies (hybrid/semantic/keyword/graph/metadata) delegates to the
right underlying CIS Phase 3 Prompt 1/2 service with the right
arguments, validation errors for strategies missing required input, and
``RetrievalCompletedEvent`` publication — against hand-written fakes for
``HybridSearchService``, ``KnowledgeGraphService``, and
``SearchService`` (real Qdrant/OpenSearch/Neo4j are unreachable in this
sandbox — see cerebrum.application.semantic's test precedents).
"""

import uuid

import pytest

from cerebrum.application.retrieval.events import RetrievalCompletedEvent
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalService,
    RetrievalStrategy,
)
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.shared.errors.exceptions import ValidationException

pytestmark = pytest.mark.unit


def _hit(source_id: str = "s1") -> SearchHit:
    return SearchHit(
        source_id=source_id,
        kind="chunk",
        title="Title",
        snippet="Snippet",
        fused_score=0.5,
        vector_score=0.9,
        keyword_score=3.0,
        citation=Citation(
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            entity_id=None,
            confidence=0.9,
            provenance={},
        ),
    )


class _FakeHybridSearchService:
    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self.hits = hits if hits is not None else [_hit()]
        self.calls: list[dict] = []

    async def search(self, query_text: str, *, workspace_id, **kwargs) -> list:
        self.calls.append({"query_text": query_text, **kwargs})
        return self.hits[: kwargs.get("limit", 10)]


class _FakeKnowledgeGraphService:
    def __init__(self, neighbors: list[dict] | None = None) -> None:
        self.neighbors = neighbors if neighbors is not None else []
        self.calls: list[dict] = []

    async def get_neighbors(self, entity_id, *, workspace_id, depth: int = 1) -> list:
        self.calls.append({"entity_id": entity_id, "depth": depth})
        return self.neighbors


class _FakeSearchService:
    def __init__(self, response: dict | None = None) -> None:
        self.response = response if response is not None else {"hits": {"hits": []}}

    async def search_by_metadata(self, *, workspace_id, **kwargs) -> dict:
        return self.response


def _service(
    *,
    hybrid: _FakeHybridSearchService | None = None,
    graph: _FakeKnowledgeGraphService | None = None,
    search: _FakeSearchService | None = None,
    events: EventDispatcher | None = None,
) -> RetrievalService:
    return RetrievalService(
        hybrid_search_service=hybrid or _FakeHybridSearchService(),  # type: ignore[arg-type]
        knowledge_graph_service=graph or _FakeKnowledgeGraphService(),  # type: ignore[arg-type]
        search_service=search or _FakeSearchService(),  # type: ignore[arg-type]
        event_dispatcher=events or EventDispatcher(),
    )


async def test_hybrid_strategy_passes_both_weights_through() -> None:
    hybrid = _FakeHybridSearchService()
    service = _service(hybrid=hybrid)

    result = await service.retrieve(
        "acme",
        workspace_id=uuid.uuid4(),
        strategy=RetrievalStrategy.HYBRID,
        vector_weight=0.7,
        keyword_weight=0.3,
    )

    assert result.strategy is RetrievalStrategy.HYBRID
    assert hybrid.calls[0]["vector_weight"] == 0.7
    assert hybrid.calls[0]["keyword_weight"] == 0.3
    assert len(result.hits) == 1


async def test_semantic_strategy_zeroes_keyword_weight() -> None:
    hybrid = _FakeHybridSearchService()
    service = _service(hybrid=hybrid)

    await service.retrieve(
        "acme", workspace_id=uuid.uuid4(), strategy=RetrievalStrategy.SEMANTIC
    )

    assert hybrid.calls[0]["keyword_weight"] == 0.0
    assert hybrid.calls[0]["vector_weight"] == 1.0


async def test_keyword_strategy_zeroes_vector_weight() -> None:
    hybrid = _FakeHybridSearchService()
    service = _service(hybrid=hybrid)

    await service.retrieve(
        "acme", workspace_id=uuid.uuid4(), strategy=RetrievalStrategy.KEYWORD
    )

    assert hybrid.calls[0]["vector_weight"] == 0.0
    assert hybrid.calls[0]["keyword_weight"] == 1.0


@pytest.mark.parametrize(
    "strategy",
    [RetrievalStrategy.HYBRID, RetrievalStrategy.SEMANTIC, RetrievalStrategy.KEYWORD],
)
async def test_text_strategies_require_query_text(
    strategy: RetrievalStrategy,
) -> None:
    service = _service()
    with pytest.raises(ValidationException):
        await service.retrieve(workspace_id=uuid.uuid4(), strategy=strategy)


async def test_graph_strategy_requires_entity_id() -> None:
    service = _service()
    with pytest.raises(ValidationException):
        await service.retrieve(
            workspace_id=uuid.uuid4(), strategy=RetrievalStrategy.GRAPH
        )


async def test_graph_strategy_builds_hits_from_neighbor_nodes() -> None:
    neighbor_id = uuid.uuid4()
    graph = _FakeKnowledgeGraphService(
        neighbors=[
            {
                "id": str(neighbor_id),
                "canonical_name": "Acme Corp",
                "confidence": 0.75,
                "entity_type": "organization",
            }
        ]
    )
    service = _service(graph=graph)
    seed_id = uuid.uuid4()

    result = await service.retrieve(
        workspace_id=uuid.uuid4(),
        strategy=RetrievalStrategy.GRAPH,
        entity_id=seed_id,
        depth=2,
    )

    assert graph.calls[0]["entity_id"] == seed_id
    assert graph.calls[0]["depth"] == 2
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.source_id == str(neighbor_id)
    assert hit.kind == "entity"
    assert hit.title == "Acme Corp"
    assert hit.citation.entity_id == neighbor_id
    assert hit.citation.confidence == 0.75
    assert result.seed_entity_id == seed_id


async def test_metadata_strategy_builds_hits_from_opensearch_response() -> None:
    document_id = uuid.uuid4()
    search = _FakeSearchService(
        response={
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "source_id": "doc-1",
                            "kind": "document",
                            "title": "Report",
                            "content": "Some report content",
                            "document_id": str(document_id),
                            "document_version_id": None,
                            "chunk_id": None,
                            "entity_id": None,
                        }
                    }
                ]
            }
        }
    )
    service = _service(search=search)

    result = await service.retrieve(
        workspace_id=uuid.uuid4(), strategy=RetrievalStrategy.METADATA, tags=["report"]
    )

    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.source_id == "doc-1"
    assert hit.citation.document_id == document_id
    assert hit.citation.confidence == 1.0


async def test_retrieve_publishes_retrieval_completed_event() -> None:
    events = EventDispatcher()
    received: list[RetrievalCompletedEvent] = []
    events.subscribe(RetrievalCompletedEvent, received.append)
    service = _service(events=events)
    workspace_id = uuid.uuid4()

    await service.retrieve(
        "acme", workspace_id=workspace_id, strategy=RetrievalStrategy.HYBRID
    )

    assert len(received) == 1
    assert received[0].workspace_id == workspace_id
    assert received[0].strategy == "hybrid"
    assert received[0].result_count == 1
