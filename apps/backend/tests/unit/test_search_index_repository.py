"""Proves CIS Phase 3 Prompt 2's OpenSearch integration
(``SearchIndexRepository``) against a fake ``AsyncOpenSearch`` client
— real OpenSearch is unreachable in this sandbox. Checks index-then-
search round trips (via a naive substring-match fake, standing in for
BM25), deterministic document IDs, workspace-scoped filtering, and
document-version-scoped deletion.
"""

from datetime import UTC, datetime

import pytest

from cerebrum.repositories.opensearch.search_index_repository import (
    SearchIndexRepository,
    document_id_for,
)

pytestmark = pytest.mark.unit


class _FakeIndicesClient:
    def __init__(self) -> None:
        self.created = False

    async def exists(self, *, index: str) -> bool:
        return self.created

    async def create(self, *, index: str, body: dict) -> None:
        self.created = True


class _FakeAsyncOpenSearch:
    def __init__(self) -> None:
        self.indices = _FakeIndicesClient()
        self.documents: dict[str, dict] = {}

    async def index(self, *, index: str, id: str, body: dict) -> None:
        self.documents[id] = body

    async def delete_by_query(self, *, index: str, body: dict) -> None:
        term = body["query"]["term"]
        ((field, value),) = term.items()
        self.documents = {
            doc_id: doc
            for doc_id, doc in self.documents.items()
            if doc.get(field) != value
        }

    async def search(self, *, index: str, body: dict) -> dict:
        query = body["query"]["bool"]
        query_text = query["must"][0]["multi_match"]["query"].lower()
        filters = query.get("filter", [])
        hits = []
        for doc_id, doc in self.documents.items():
            if (
                query_text not in doc.get("content", "").lower()
                and query_text not in doc.get("title", "").lower()
            ):
                continue
            if not self._matches_filters(doc, filters):
                continue
            hits.append({"_id": doc_id, "_score": 1.0, "_source": doc})
        return {
            "hits": {
                "hits": hits[
                    body.get("from", 0) : body.get("from", 0) + body.get("size", 10)
                ]
            },
            "aggregations": {},
        }

    async def count(self, *, index: str, body: dict) -> dict:
        term = body["query"]["term"]
        ((field, value),) = term.items()
        matching = [doc for doc in self.documents.values() if doc.get(field) == value]
        return {"count": len(matching)}

    @staticmethod
    def _matches_filters(doc: dict, filters: list[dict]) -> bool:
        for condition in filters:
            if "term" in condition:
                ((field, value),) = condition["term"].items()
                if doc.get(field) != value:
                    return False
            if "terms" in condition:
                ((field, values),) = condition["terms"].items()
                doc_value = doc.get(field)
                if isinstance(doc_value, list):
                    if not set(doc_value) & set(values):
                        return False
                elif doc_value not in values:
                    return False
        return True


def _repository() -> tuple[SearchIndexRepository, _FakeAsyncOpenSearch]:
    client = _FakeAsyncOpenSearch()
    return SearchIndexRepository(client), client  # type: ignore[arg-type]


async def test_document_id_is_deterministic_by_kind_and_source_id() -> None:
    assert document_id_for("chunk", "abc") == document_id_for("chunk", "abc")
    assert document_id_for("chunk", "abc") != document_id_for("entity", "abc")


async def test_ensure_index_creates_it_once() -> None:
    repository, client = _repository()
    await repository.ensure_index()
    assert client.indices.created is True


async def test_index_then_search_finds_the_artifact_by_content() -> None:
    repository, _client = _repository()
    await repository.index_artifact(
        kind="chunk",
        source_id="c1",
        workspace_id="ws1",
        organization_id="org1",
        document_id="d1",
        document_version_id="v1",
        chunk_id="c1",
        entity_id=None,
        title="Report",
        content="Acme Corp signed the deal.",
        tags=[],
        created_at=datetime.now(UTC),
    )

    response = await repository.search(query_text="Acme", workspace_id="ws1")
    hits = response["hits"]["hits"]
    assert len(hits) == 1
    assert hits[0]["_source"]["source_id"] == "c1"


async def test_search_is_scoped_to_workspace() -> None:
    repository, _client = _repository()
    for workspace_id in ("ws1", "ws2"):
        await repository.index_artifact(
            kind="chunk",
            source_id=workspace_id,
            workspace_id=workspace_id,
            organization_id="org",
            document_id="d",
            document_version_id="v",
            chunk_id=None,
            entity_id=None,
            title="Shared",
            content="shared content",
            tags=[],
            created_at=datetime.now(UTC),
        )

    response = await repository.search(query_text="shared", workspace_id="ws1")
    hits = response["hits"]["hits"]
    assert len(hits) == 1
    assert hits[0]["_source"]["workspace_id"] == "ws1"


async def test_search_filters_by_tags() -> None:
    repository, _client = _repository()
    await repository.index_artifact(
        kind="entity",
        source_id="e1",
        workspace_id="ws1",
        organization_id="org1",
        document_id="d1",
        document_version_id=None,
        chunk_id=None,
        entity_id="e1",
        title="Acme",
        content="Acme entity",
        tags=["organization"],
        created_at=datetime.now(UTC),
    )
    await repository.index_artifact(
        kind="entity",
        source_id="e2",
        workspace_id="ws1",
        organization_id="org1",
        document_id="d1",
        document_version_id=None,
        chunk_id=None,
        entity_id="e2",
        title="Bob",
        content="Bob entity",
        tags=["person"],
        created_at=datetime.now(UTC),
    )

    response = await repository.search(
        query_text="entity", workspace_id="ws1", tags=["organization"]
    )
    hits = response["hits"]["hits"]
    assert len(hits) == 1
    assert hits[0]["_source"]["source_id"] == "e1"


async def test_reindexing_the_same_source_overwrites_the_document() -> None:
    repository, client = _repository()
    await repository.index_artifact(
        kind="chunk",
        source_id="c1",
        workspace_id="ws1",
        organization_id="org1",
        document_id="d1",
        document_version_id="v1",
        chunk_id="c1",
        entity_id=None,
        title="Old title",
        content="old content",
        tags=[],
        created_at=datetime.now(UTC),
    )
    await repository.index_artifact(
        kind="chunk",
        source_id="c1",
        workspace_id="ws1",
        organization_id="org1",
        document_id="d1",
        document_version_id="v1",
        chunk_id="c1",
        entity_id=None,
        title="New title",
        content="new content",
        tags=[],
        created_at=datetime.now(UTC),
    )

    assert len(client.documents) == 1
    doc = next(iter(client.documents.values()))
    assert doc["title"] == "New title"


async def test_delete_by_document_version_removes_only_matching_documents() -> None:
    repository, client = _repository()
    for version_id in ("v1", "v2"):
        await repository.index_artifact(
            kind="chunk",
            source_id=version_id,
            workspace_id="ws1",
            organization_id="org1",
            document_id="d1",
            document_version_id=version_id,
            chunk_id=None,
            entity_id=None,
            title="T",
            content="content",
            tags=[],
            created_at=datetime.now(UTC),
        )

    await repository.delete_by_document_version("v1")

    assert len(client.documents) == 1
    remaining = next(iter(client.documents.values()))
    assert remaining["document_version_id"] == "v2"


async def test_count_scoped_to_workspace() -> None:
    repository, _client = _repository()
    for i in range(3):
        await repository.index_artifact(
            kind="chunk",
            source_id=str(i),
            workspace_id="ws1",
            organization_id="org1",
            document_id="d1",
            document_version_id="v1",
            chunk_id=None,
            entity_id=None,
            title="T",
            content="content",
            tags=[],
            created_at=datetime.now(UTC),
        )

    assert await repository.count(workspace_id="ws1") == 3
    assert await repository.count(workspace_id="ws2") == 0
