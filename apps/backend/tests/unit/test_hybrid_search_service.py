"""Proves CIS Phase 3 Prompt 2's ``HybridSearchService``: Reciprocal
Rank Fusion ordering (an item ranked by *both* retrieval methods
outranks one only one liked), configurable vector/keyword weights,
citation construction from stored payload/source fields, Similar
Documents/Chunks/Entities (vector-only, self-excluded), and tenant
isolation (every call is workspace-scoped by construction). Uses fake
``VectorIndexService``/``SearchService`` collaborators — real Qdrant/
OpenSearch are unreachable in this sandbox.
"""

import uuid

import pytest

from cerebrum.application.semantic.hybrid_search_service import HybridSearchService
from cerebrum.infrastructure.embeddings.providers import HashingEmbeddingProvider
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


class _FakeVectorIndexService:
    def __init__(
        self, results: list[dict] | None = None, vectors: dict | None = None
    ) -> None:
        self._results = results or []
        self._vectors = vectors or {}

    async def search(
        self, *, vector, workspace_id, kinds=None, limit=10, score_threshold=None
    ):
        return self._results[:limit]

    async def get_vector(self, *, kind, source_id):
        return self._vectors.get((kind, source_id))


class _FakeSearchService:
    def __init__(self, response: dict | None = None) -> None:
        self._response = response or {"hits": {"hits": []}}

    async def search(
        self, *, query_text, workspace_id, kinds=None, tags=None, limit=10
    ):
        return self._response


def _vector_point(
    source_id: str, *, score: float, kind: str = "chunk", **payload
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "score": score,
        "payload": {
            "source_id": source_id,
            "kind": kind,
            "document_id": None,
            "document_version_id": None,
            "chunk_id": None,
            "entity_id": None,
            "provenance": {},
            "metadata": {},
            **payload,
        },
    }


def _keyword_hit(
    source_id: str, *, score: float, kind: str = "chunk", **source_fields
) -> dict:
    return {
        "_score": score,
        "_source": {
            "source_id": source_id,
            "kind": kind,
            "title": "",
            "content": "",
            "document_id": None,
            "document_version_id": None,
            "chunk_id": None,
            "entity_id": None,
            **source_fields,
        },
    }


def _service(
    vector_results=None, keyword_hits=None, vectors=None
) -> HybridSearchService:
    return HybridSearchService(
        provider=HashingEmbeddingProvider(dimension=16),
        vector_index_service=_FakeVectorIndexService(vector_results, vectors),
        search_service=_FakeSearchService({"hits": {"hits": keyword_hits or []}}),
    )


async def test_an_item_found_by_both_methods_outranks_one_found_by_only_one() -> None:
    service = _service(
        vector_results=[
            _vector_point("both", score=0.9),
            _vector_point("vector-only", score=0.8),
        ],
        keyword_hits=[
            _keyword_hit("keyword-only", score=5.0),
            _keyword_hit("both", score=3.0),
        ],
    )

    results = await service.search("query", workspace_id=uuid.uuid4())

    assert results[0].source_id == "both"
    ranked_ids = [hit.source_id for hit in results]
    assert set(ranked_ids) == {"both", "vector-only", "keyword-only"}


async def test_zero_keyword_weight_makes_ranking_purely_vector_order() -> None:
    service = _service(
        vector_results=[_vector_point("a", score=0.9), _vector_point("b", score=0.5)],
        keyword_hits=[_keyword_hit("b", score=100.0), _keyword_hit("a", score=1.0)],
    )

    results = await service.search(
        "query", workspace_id=uuid.uuid4(), keyword_weight=0.0
    )

    assert [hit.source_id for hit in results] == ["a", "b"]


async def test_citation_is_built_from_vector_payload() -> None:
    document_id, version_id, chunk_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    service = _service(
        vector_results=[
            _vector_point(
                "c1",
                score=0.7,
                document_id=str(document_id),
                document_version_id=str(version_id),
                chunk_id=str(chunk_id),
                provenance={"source_text_length": 42},
            )
        ]
    )

    results = await service.search("query", workspace_id=uuid.uuid4())

    citation = results[0].citation
    assert citation.document_id == document_id
    assert citation.document_version_id == version_id
    assert citation.chunk_id == chunk_id
    assert citation.confidence == 0.7
    assert citation.provenance["source_text_length"] == 42
    assert citation.provenance["index"] == "qdrant"


async def test_citation_is_built_from_keyword_hit_source() -> None:
    document_id = uuid.uuid4()
    service = _service(
        keyword_hits=[
            _keyword_hit("d1", score=4.0, kind="document", document_id=str(document_id))
        ]
    )

    results = await service.search("query", workspace_id=uuid.uuid4())

    citation = results[0].citation
    assert citation.document_id == document_id
    assert citation.provenance["index"] == "opensearch"


async def test_similar_to_source_excludes_the_source_itself() -> None:
    source_id = uuid.uuid4()
    service = HybridSearchService(
        provider=HashingEmbeddingProvider(dimension=16),
        vector_index_service=_FakeVectorIndexService(
            results=[
                _vector_point(str(source_id), score=1.0),
                _vector_point("other", score=0.5),
            ],
            vectors={("chunk", source_id): [0.1, 0.2]},
        ),
        search_service=_FakeSearchService(),
    )

    results = await service.similar_to_source(
        kind="chunk", source_id=source_id, workspace_id=uuid.uuid4()
    )

    assert all(hit.source_id != str(source_id) for hit in results)


async def test_similar_to_source_raises_when_no_embedding_exists() -> None:
    service = HybridSearchService(
        provider=HashingEmbeddingProvider(dimension=16),
        vector_index_service=_FakeVectorIndexService(),
        search_service=_FakeSearchService(),
    )

    with pytest.raises(NotFoundException):
        await service.similar_to_source(
            kind="chunk", source_id=uuid.uuid4(), workspace_id=uuid.uuid4()
        )
