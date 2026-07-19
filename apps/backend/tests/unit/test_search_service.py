"""Proves CIS Phase 3 Prompt 2's ``SearchService``: indexing documents/
chunks/entities, ``index_version``'s aggregate indexing + event
emission, and the search/autocomplete/statistics pass-throughs —
against a fake ``SearchIndexRepository`` (real OpenSearch is
unreachable in this sandbox). Model instances are constructed directly
in memory rather than persisted — ``SearchService`` only reads their
attributes, so no database round trip is needed for this service-level
test.
"""

import uuid
from datetime import UTC, datetime

import pytest

from cerebrum.application.semantic.events import SearchIndexUpdatedEvent
from cerebrum.application.semantic.search_service import SearchService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk
from cerebrum.infrastructure.database.models.document import Document
from cerebrum.infrastructure.database.models.entity import Entity

pytestmark = pytest.mark.unit


class _FakeSearchIndexRepository:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}
        self.ensured = False

    async def ensure_index(self) -> None:
        self.ensured = True

    async def index_artifact(self, *, kind, source_id, **fields) -> None:
        self.documents[f"{kind}:{source_id}"] = {
            "kind": kind,
            "source_id": source_id,
            **fields,
        }

    async def delete_by_document_version(self, document_version_id) -> None:
        self.documents = {
            k: v
            for k, v in self.documents.items()
            if v.get("document_version_id") != document_version_id
        }

    async def search(self, **kwargs) -> dict:
        return {"hits": {"hits": []}}

    async def autocomplete(self, **kwargs) -> list:
        return ["Suggested Title"]

    async def count(self, *, workspace_id: str) -> int:
        return sum(
            1 for doc in self.documents.values() if doc["workspace_id"] == workspace_id
        )


def _document(name: str = "Report.pdf") -> Document:
    return Document(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        folder_id=None,
        name=name,
        status="draft",
        current_version_id=None,
        created_at=datetime.now(UTC),
    )


def _chunk(document_version_id: uuid.UUID, text: str = "chunk text") -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        document_version_id=document_version_id,
        extraction_id=uuid.uuid4(),
        strategy="paragraph",
        chunk_index=0,
        text=text,
        character_count=len(text),
        start_offset=0,
        end_offset=len(text),
        overlap_with_previous=0,
        chunk_metadata={},
        created_at=datetime.now(UTC),
    )


def _entity(canonical_name: str = "Acme Corp") -> Entity:
    return Entity(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        entity_type="organization",
        canonical_name=canonical_name,
        aliases=[],
        description=None,
        confidence=0.8,
        provenance=[],
        created_at=datetime.now(UTC),
    )


def _service(
    repository: _FakeSearchIndexRepository | None = None,
    *,
    events: EventDispatcher | None = None,
):
    return SearchService(
        search_index_repository=repository or _FakeSearchIndexRepository(),
        event_dispatcher=events or EventDispatcher(),
    )


async def test_index_document_stores_it_under_the_document_kind() -> None:
    repository = _FakeSearchIndexRepository()
    service = _service(repository)
    document = _document()

    await service.index_document(
        document, workspace_id=document.workspace_id, organization_id=uuid.uuid4()
    )

    key = f"document:{document.id}"
    assert key in repository.documents
    assert repository.documents[key]["title"] == "Report.pdf"


async def test_index_chunk_uses_the_owning_documents_title() -> None:
    repository = _FakeSearchIndexRepository()
    service = _service(repository)
    document = _document(name="Handbook.pdf")
    chunk = _chunk(uuid.uuid4(), text="Employee handbook content.")

    await service.index_chunk(
        chunk,
        document=document,
        workspace_id=document.workspace_id,
        organization_id=uuid.uuid4(),
    )

    key = f"chunk:{chunk.id}"
    assert repository.documents[key]["title"] == "Handbook.pdf"
    assert repository.documents[key]["content"] == "Employee handbook content."


async def test_index_entity_falls_back_to_canonical_name_without_a_description() -> (
    None
):
    repository = _FakeSearchIndexRepository()
    service = _service(repository)
    entity = _entity()

    await service.index_entity(
        entity, workspace_id=entity.workspace_id, organization_id=entity.organization_id
    )

    key = f"entity:{entity.id}"
    assert repository.documents[key]["content"] == "Acme Corp"
    assert repository.documents[key]["tags"] == ["organization"]


async def test_index_version_indexes_document_chunks_entities_then_emits() -> None:
    repository = _FakeSearchIndexRepository()
    events = EventDispatcher()
    received: list[SearchIndexUpdatedEvent] = []
    events.subscribe(SearchIndexUpdatedEvent, received.append)
    service = _service(repository, events=events)

    document = _document()
    version_id = uuid.uuid4()
    chunks = [_chunk(version_id), _chunk(version_id)]
    entities = [_entity("Alice"), _entity("Bob"), _entity("Carol")]
    workspace_id, organization_id = uuid.uuid4(), uuid.uuid4()

    indexed_count = await service.index_version(
        document=document,
        document_version_id=version_id,
        chunks=chunks,
        entities=entities,
        workspace_id=workspace_id,
        organization_id=organization_id,
    )

    assert indexed_count == 1 + len(chunks) + len(entities)
    assert len(repository.documents) == indexed_count
    assert len(received) == 1
    assert received[0].indexed_count == indexed_count
    assert received[0].document_version_id == version_id


async def test_autocomplete_and_statistics_pass_through() -> None:
    repository = _FakeSearchIndexRepository()
    service = _service(repository)
    workspace_id = uuid.uuid4()
    await service.index_document(
        _document(), workspace_id=workspace_id, organization_id=uuid.uuid4()
    )

    suggestions = await service.autocomplete(prefix="Rep", workspace_id=workspace_id)
    assert suggestions == ["Suggested Title"]

    statistics = await service.get_statistics(workspace_id=workspace_id)
    assert statistics == {"indexed_document_count": 1}
