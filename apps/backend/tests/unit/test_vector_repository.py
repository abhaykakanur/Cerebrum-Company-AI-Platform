"""Proves CIS Phase 3 Prompt 2's Qdrant integration
(``VectorRepository``) against a fake ``AsyncQdrantClient`` — real
Qdrant is unreachable in this sandbox (same reasoning as
test_knowledge_graph_repository.py's fake Neo4j driver for the same
class of dependency). Checks upsert-then-retrieve round trips,
deterministic point IDs, workspace-scoped search/statistics, and
document-version-scoped deletion.
"""

import uuid
from dataclasses import dataclass, field

import pytest

from cerebrum.repositories.qdrant.vector_repository import (
    VectorRepository,
    point_id_for,
)

pytestmark = pytest.mark.unit


@dataclass
class _FakePoint:
    id: str
    payload: dict
    vector: list[float] = field(default_factory=list)


@dataclass
class _FakeScoredPoint:
    id: str
    score: float
    payload: dict


@dataclass
class _FakeQueryResponse:
    points: list


@dataclass
class _FakeCountResult:
    count: int


class _FakeAsyncQdrantClient:
    def __init__(self) -> None:
        self.points: dict[str, _FakePoint] = {}
        self.collection_created = False

    async def collection_exists(self, collection_name: str) -> bool:
        return self.collection_created

    async def create_collection(self, *, collection_name: str, vectors_config) -> bool:
        self.collection_created = True
        return True

    async def upsert(self, *, collection_name: str, points, **kwargs) -> None:
        for point in points:
            self.points[str(point.id)] = _FakePoint(
                id=str(point.id), payload=point.payload, vector=point.vector
            )

    async def retrieve(
        self, *, collection_name: str, ids, with_payload=True, with_vectors=False
    ):
        return [self.points[str(i)] for i in ids if str(i) in self.points]

    async def delete(self, *, collection_name: str, points_selector) -> None:
        # points_selector is a Filter with one FieldCondition(key, match=MatchValue)
        condition = points_selector.must[0]
        key, value = condition.key, condition.match.value
        self.points = {
            pid: p for pid, p in self.points.items() if p.payload.get(key) != value
        }

    async def query_points(
        self,
        *,
        collection_name: str,
        query,
        query_filter,
        limit,
        score_threshold,
        with_payload,
    ) -> _FakeQueryResponse:
        must_conditions = query_filter.must or []
        should_conditions = query_filter.should or []
        results = []
        for point in self.points.values():
            if not all(
                point.payload.get(c.key) == c.match.value for c in must_conditions
            ):
                continue
            if should_conditions and not any(
                point.payload.get(c.key) == c.match.value for c in should_conditions
            ):
                continue
            score = _cosine(query, point.vector) if point.vector else 0.0
            results.append(
                _FakeScoredPoint(id=point.id, score=score, payload=point.payload)
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return _FakeQueryResponse(points=results[:limit])

    async def count(self, *, collection_name: str, count_filter) -> _FakeCountResult:
        condition = count_filter.must[0]
        matching = [
            p
            for p in self.points.values()
            if p.payload.get(condition.key) == condition.match.value
        ]
        return _FakeCountResult(count=len(matching))


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=False))


def _repository() -> tuple[VectorRepository, _FakeAsyncQdrantClient]:
    client = _FakeAsyncQdrantClient()
    return VectorRepository(client, vector_size=4), client  # type: ignore[arg-type]


async def test_point_id_is_deterministic_by_kind_and_source_id() -> None:
    source_id = uuid.uuid4()
    assert point_id_for("chunk", source_id) == point_id_for("chunk", source_id)
    assert point_id_for("chunk", source_id) != point_id_for("entity", source_id)


async def test_ensure_collection_creates_it_once() -> None:
    repository, client = _repository()
    await repository.ensure_collection()
    assert client.collection_created is True


async def test_upsert_then_get_point_round_trips() -> None:
    repository, _client = _repository()
    workspace_id, document_id, version_id, source_id = (
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    )

    await repository.upsert_point(
        kind="chunk",
        source_id=source_id,
        vector=[1.0, 0.0, 0.0, 0.0],
        chunk_id=source_id,
        entity_id=None,
        document_id=document_id,
        document_version_id=version_id,
        workspace_id=workspace_id,
        organization_id=uuid.uuid4(),
        embedding_model="test-model",
        embedding_version="test-model",
        metadata={},
        provenance={},
    )

    point = await repository.get_point("chunk", source_id)
    assert point is not None
    assert point["payload"]["embedding_model"] == "test-model"
    assert point["vector"] == [1.0, 0.0, 0.0, 0.0]


async def test_get_point_returns_none_when_absent() -> None:
    repository, _client = _repository()
    assert await repository.get_point("chunk", uuid.uuid4()) is None


async def test_reupserting_the_same_source_overwrites_the_point() -> None:
    repository, client = _repository()
    source_id = uuid.uuid4()
    common = {
        "chunk_id": source_id,
        "entity_id": None,
        "document_id": uuid.uuid4(),
        "document_version_id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "metadata": {},
        "provenance": {},
    }
    await repository.upsert_point(
        kind="chunk",
        source_id=source_id,
        vector=[1.0, 0.0, 0.0, 0.0],
        embedding_model="v1",
        embedding_version="v1",
        **common,
    )
    await repository.upsert_point(
        kind="chunk",
        source_id=source_id,
        vector=[0.0, 1.0, 0.0, 0.0],
        embedding_model="v2",
        embedding_version="v2",
        **common,
    )

    assert len(client.points) == 1
    point = await repository.get_point("chunk", source_id)
    assert point is not None
    assert point["payload"]["embedding_version"] == "v2"


async def test_search_is_scoped_to_workspace() -> None:
    repository, _client = _repository()
    workspace_a, workspace_b = uuid.uuid4(), uuid.uuid4()
    for workspace_id in (workspace_a, workspace_b):
        await repository.upsert_point(
            kind="chunk",
            source_id=uuid.uuid4(),
            vector=[1.0, 0.0, 0.0, 0.0],
            chunk_id=None,
            entity_id=None,
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            workspace_id=workspace_id,
            organization_id=uuid.uuid4(),
            embedding_model="m",
            embedding_version="m",
            metadata={},
            provenance={},
        )

    results = await repository.search(
        vector=[1.0, 0.0, 0.0, 0.0], workspace_id=workspace_a
    )
    assert len(results) == 1
    assert results[0]["payload"]["workspace_id"] == str(workspace_a)


async def test_delete_by_document_version_removes_only_matching_points() -> None:
    repository, client = _repository()
    version_to_delete, version_to_keep = uuid.uuid4(), uuid.uuid4()
    for version_id in (version_to_delete, version_to_keep):
        await repository.upsert_point(
            kind="chunk",
            source_id=uuid.uuid4(),
            vector=[1.0, 0.0, 0.0, 0.0],
            chunk_id=None,
            entity_id=None,
            document_id=uuid.uuid4(),
            document_version_id=version_id,
            workspace_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            embedding_model="m",
            embedding_version="m",
            metadata={},
            provenance={},
        )

    await repository.delete_by_document_version(version_to_delete)

    assert len(client.points) == 1
    remaining = next(iter(client.points.values()))
    assert remaining.payload["document_version_id"] == str(version_to_keep)


async def test_get_statistics_counts_points_for_workspace() -> None:
    repository, _client = _repository()
    workspace_id = uuid.uuid4()
    for _ in range(3):
        await repository.upsert_point(
            kind="chunk",
            source_id=uuid.uuid4(),
            vector=[1.0, 0.0, 0.0, 0.0],
            chunk_id=None,
            entity_id=None,
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            workspace_id=workspace_id,
            organization_id=uuid.uuid4(),
            embedding_model="m",
            embedding_version="m",
            metadata={},
            provenance={},
        )

    statistics = await repository.get_statistics(workspace_id)
    assert statistics == {"vector_count": 3}
