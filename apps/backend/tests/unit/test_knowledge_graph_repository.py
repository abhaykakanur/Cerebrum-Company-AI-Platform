"""Proves CIS Phase 3 Prompt 1's Neo4j integration
(``KnowledgeGraphRepository``) against a fake ``AsyncDriver``/
``AsyncSession`` — real Neo4j is unreachable in this sandbox (same
reasoning as test_upload_service.py's ``_FakeUploader`` for MinIO).
Checks both directions: writes issue ``session.run()`` with the
expected Cypher shape and parameter names, and result-parsing methods
correctly turn driver records back into plain Python values.
"""

import uuid

import pytest

from cerebrum.repositories.neo4j.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)

pytestmark = pytest.mark.unit


class _FakeAsyncResult:
    def __init__(self, records: list[dict]) -> None:
        self._records = records

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for record in self._records:
            yield record

    async def single(self) -> dict | None:
        return self._records[0] if self._records else None


class _FakeAsyncSession:
    def __init__(self, driver: "_FakeAsyncDriver") -> None:
        self._driver = driver

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, *exc_info) -> bool:
        return False

    async def run(self, query: str, **params) -> _FakeAsyncResult:
        self._driver.calls.append((query, params))
        return self._driver.result_for(query, params)


class _FakeAsyncDriver:
    def __init__(self, records: list[dict] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._records = records or []

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)

    def result_for(self, query: str, params: dict) -> _FakeAsyncResult:
        return _FakeAsyncResult(self._records)


async def test_upsert_entity_node_issues_a_merge_with_expected_params() -> None:
    driver = _FakeAsyncDriver()
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]
    entity_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    await repository.upsert_entity_node(
        entity_id=entity_id,
        workspace_id=workspace_id,
        entity_type="organization",
        canonical_name="Acme Corp",
        aliases=["Acme"],
        confidence=0.9,
    )

    assert len(driver.calls) == 1
    query, params = driver.calls[0]
    assert "MERGE (e:Entity {id: $id})" in query
    assert params["id"] == str(entity_id)
    assert params["workspace_id"] == str(workspace_id)
    assert params["canonical_name"] == "Acme Corp"
    assert params["aliases"] == ["Acme"]
    assert params["confidence"] == 0.9


async def test_upsert_relationship_edge_issues_a_merge_with_expected_params() -> None:
    driver = _FakeAsyncDriver()
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]
    relationship_id, source_id, target_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    await repository.upsert_relationship_edge(
        relationship_id=relationship_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type="reports_to",
        confidence=0.7,
    )

    query, params = driver.calls[0]
    assert "MERGE (source)-[r:RELATES_TO {id: $id}]->(target)" in query
    assert params["source_id"] == str(source_id)
    assert params["target_id"] == str(target_id)
    assert params["relationship_type"] == "reports_to"


async def test_soft_delete_entity_node_marks_node_and_incident_edges() -> None:
    driver = _FakeAsyncDriver()
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]
    entity_id = uuid.uuid4()

    await repository.soft_delete_entity_node(entity_id)

    query, params = driver.calls[0]
    assert "SET e.is_deleted = true" in query
    assert "SET r.is_deleted = true" in query
    assert params["id"] == str(entity_id)


async def test_get_neighbors_parses_records_into_plain_dicts() -> None:
    node_payload = {
        "id": "abc",
        "canonical_name": "Bob Williams",
        "entity_type": "person",
        "aliases": [],
        "confidence": 0.6,
        "workspace_id": "ws-1",
        "is_deleted": False,
    }
    driver = _FakeAsyncDriver(records=[{"neighbor": node_payload}])
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]

    neighbors = await repository.get_neighbors(uuid.uuid4(), depth=2)

    assert neighbors == [node_payload]
    query, _params = driver.calls[0]
    assert "*1..2" in query


async def test_get_statistics_parses_the_single_record() -> None:
    driver = _FakeAsyncDriver(records=[{"entity_count": 5, "relationship_count": 3}])
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]

    statistics = await repository.get_statistics(uuid.uuid4())

    assert statistics == {"entity_count": 5, "relationship_count": 3}


async def test_get_statistics_defaults_to_zero_when_no_record() -> None:
    driver = _FakeAsyncDriver(records=[])
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]

    statistics = await repository.get_statistics(uuid.uuid4())

    assert statistics == {"entity_count": 0, "relationship_count": 0}


async def test_validate_consistency_formats_one_message_per_violation() -> None:
    relationship_id = str(uuid.uuid4())
    driver = _FakeAsyncDriver(records=[{"relationship_id": relationship_id}])
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]

    issues = await repository.validate_consistency(uuid.uuid4())

    assert len(issues) == 1
    assert relationship_id in issues[0]


async def test_validate_consistency_returns_empty_list_when_consistent() -> None:
    driver = _FakeAsyncDriver(records=[])
    repository = KnowledgeGraphRepository(driver)  # type: ignore[arg-type]

    issues = await repository.validate_consistency(uuid.uuid4())

    assert issues == []
