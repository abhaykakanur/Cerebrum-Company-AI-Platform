"""Proves CIS Phase 3 Prompt 3's ``ContextBuilderService``: resolving
hits into full documents/chunks/entities, the six Context Optimization
techniques (dedup, chunk ordering, entity grouping, metadata
enrichment, relationship expansion, compression), configurable-depth
graph-neighbor expansion, version history, and graceful handling of a
citation referencing an already-deleted entity — against hand-written
fakes for every PostgreSQL repository and
``KnowledgeGraphService`` (real Postgres/Neo4j are unreachable in this
sandbox — see cerebrum.application.semantic's test precedents).
"""

import uuid
from datetime import UTC, datetime

import pytest

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.retrieval.context_builder_service import (
    ContextBuilderService,
)
from cerebrum.application.retrieval.events import ContextBuiltEvent
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk
from cerebrum.infrastructure.database.models.document import Document
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.database.models.entity import Entity
from cerebrum.infrastructure.database.models.relationship import Relationship
from cerebrum.repositories.contracts import Page

pytestmark = pytest.mark.unit


class _FakeChunkRepository:
    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self._chunks = {c.id: c for c in (chunks or [])}

    async def get_by_id(self, chunk_id: uuid.UUID) -> Chunk | None:
        return self._chunks.get(chunk_id)


class _FakeEntityRepository:
    def __init__(self, entities: list[Entity] | None = None) -> None:
        self._entities = {e.id: e for e in (entities or [])}

    async def get_by_id(self, entity_id: uuid.UUID) -> Entity | None:
        entity = self._entities.get(entity_id)
        return None if entity is None or entity.is_deleted else entity


class _FakeRelationshipRepository:
    def __init__(self, relationships: list[Relationship] | None = None) -> None:
        self._relationships = relationships or []

    async def list_for_entity(self, entity_id: uuid.UUID) -> list[Relationship]:
        return [
            r
            for r in self._relationships
            if r.source_entity_id == entity_id or r.target_entity_id == entity_id
        ]


class _FakeDocumentRepository:
    def __init__(self, documents: list[Document] | None = None) -> None:
        self._documents = {d.id: d for d in (documents or [])}

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return self._documents.get(document_id)


class _FakeDocumentVersionRepository:
    def __init__(self, versions: list[DocumentVersion] | None = None) -> None:
        self._versions = {v.id: v for v in (versions or [])}

    async def get_by_id(self, version_id: uuid.UUID) -> DocumentVersion | None:
        return self._versions.get(version_id)

    async def get_current(self, document_id: uuid.UUID) -> DocumentVersion | None:
        for version in self._versions.values():
            if version.document_id == document_id and version.is_current:
                return version
        return None

    async def list_by_document(self, document_id: uuid.UUID, *, pagination) -> Page:
        items = [v for v in self._versions.values() if v.document_id == document_id]
        items.sort(key=lambda v: v.version_number)
        return Page(items=items, total_items=len(items), pagination=pagination)


class _FakeKnowledgeGraphService:
    def __init__(
        self, neighbors_by_entity: dict[uuid.UUID, list[dict]] | None = None
    ) -> None:
        self._neighbors = neighbors_by_entity or {}
        self.calls: list[dict] = []

    async def get_neighbors(
        self, entity_id: uuid.UUID, *, workspace_id, depth: int = 1
    ):
        self.calls.append({"entity_id": entity_id, "depth": depth})
        return self._neighbors.get(entity_id, [])


def _document(
    document_id: uuid.UUID | None = None, name: str = "Report.pdf"
) -> Document:
    return Document(
        id=document_id or uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        folder_id=None,
        name=name,
        status="active",
        current_version_id=None,
        created_at=datetime.now(UTC),
    )


def _version(
    document_id: uuid.UUID,
    *,
    version_id: uuid.UUID | None = None,
    version_number: int = 1,
    is_current: bool = True,
) -> DocumentVersion:
    return DocumentVersion(
        id=version_id or uuid.uuid4(),
        document_id=document_id,
        version_number=version_number,
        is_current=is_current,
    )


def _chunk(
    *,
    chunk_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID,
    chunk_index: int = 0,
    text: str = "chunk text",
) -> Chunk:
    return Chunk(
        id=chunk_id or uuid.uuid4(),
        document_version_id=document_version_id,
        extraction_id=uuid.uuid4(),
        strategy="paragraph",
        chunk_index=chunk_index,
        text=text,
        character_count=len(text),
        start_offset=0,
        end_offset=len(text),
        overlap_with_previous=0,
        chunk_metadata={},
        created_at=datetime.now(UTC),
    )


def _entity(
    *,
    entity_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID,
    entity_type: str = "organization",
    canonical_name: str = "Acme Corp",
    description: str | None = None,
    is_deleted: bool = False,
) -> Entity:
    return Entity(
        id=entity_id or uuid.uuid4(),
        workspace_id=workspace_id,
        organization_id=uuid.uuid4(),
        entity_type=entity_type,
        canonical_name=canonical_name,
        aliases=[],
        description=description,
        confidence=0.8,
        provenance=[],
        is_deleted=is_deleted,
        created_at=datetime.now(UTC),
    )


def _relationship(
    *, source_entity_id: uuid.UUID, target_entity_id: uuid.UUID, workspace_id: uuid.UUID
) -> Relationship:
    return Relationship(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        organization_id=uuid.uuid4(),
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relationship_type="collaboration",
        confidence=0.9,
    )


def _chunk_hit(chunk: Chunk, *, document_id: uuid.UUID) -> SearchHit:
    return SearchHit(
        source_id=str(chunk.id),
        kind="chunk",
        title="Title",
        snippet="",
        fused_score=0.5,
        vector_score=0.5,
        keyword_score=None,
        citation=Citation(
            document_id=document_id,
            document_version_id=chunk.document_version_id,
            chunk_id=chunk.id,
            entity_id=None,
            confidence=0.9,
            provenance={},
        ),
    )


def _entity_hit(entity: Entity) -> SearchHit:
    return SearchHit(
        source_id=str(entity.id),
        kind="entity",
        title=entity.canonical_name,
        snippet="",
        fused_score=0.4,
        vector_score=None,
        keyword_score=0.4,
        citation=Citation(
            document_id=None,
            document_version_id=None,
            chunk_id=None,
            entity_id=entity.id,
            confidence=entity.confidence,
            provenance={},
        ),
    )


def _service(
    *,
    chunks: list[Chunk] | None = None,
    entities: list[Entity] | None = None,
    relationships: list[Relationship] | None = None,
    documents: list[Document] | None = None,
    versions: list[DocumentVersion] | None = None,
    graph: _FakeKnowledgeGraphService | None = None,
    events: EventDispatcher | None = None,
) -> ContextBuilderService:
    return ContextBuilderService(
        chunk_repository=_FakeChunkRepository(chunks),  # type: ignore[arg-type]
        entity_service=EntityService(
            entity_repository=_FakeEntityRepository(entities)  # type: ignore[arg-type]
        ),
        relationship_service=RelationshipService(
            relationship_repository=_FakeRelationshipRepository(relationships)  # type: ignore[arg-type]
        ),
        document_repository=_FakeDocumentRepository(documents),  # type: ignore[arg-type]
        version_repository=_FakeDocumentVersionRepository(versions),  # type: ignore[arg-type]
        knowledge_graph_service=graph or _FakeKnowledgeGraphService(),  # type: ignore[arg-type]
        event_dispatcher=events or EventDispatcher(),
    )


async def test_build_resolves_chunks_entities_and_documents() -> None:
    workspace_id = uuid.uuid4()
    document = _document()
    version = _version(document.id)
    chunk = _chunk(document_version_id=version.id, text="Hello world")
    entity = _entity(workspace_id=workspace_id)

    service = _service(
        chunks=[chunk],
        entities=[entity],
        documents=[document],
        versions=[version],
    )
    hits = [_chunk_hit(chunk, document_id=document.id), _entity_hit(entity)]

    package = await service.build(hits, workspace_id=workspace_id)

    assert len(package.chunks) == 1
    assert package.chunks[0].text == "Hello world"
    assert len(package.entities) == 1
    assert package.entities[0].canonical_name == "Acme Corp"
    assert len(package.documents) == 1
    assert package.documents[0].name == "Report.pdf"
    assert package.truncated is False


async def test_chunks_are_ordered_by_chunk_index_not_hit_order() -> None:
    workspace_id = uuid.uuid4()
    document = _document()
    version = _version(document.id)
    first = _chunk(document_version_id=version.id, chunk_index=0, text="first")
    second = _chunk(document_version_id=version.id, chunk_index=1, text="second")

    service = _service(chunks=[first, second], documents=[document], versions=[version])
    hits = [
        _chunk_hit(second, document_id=document.id),
        _chunk_hit(first, document_id=document.id),
    ]

    package = await service.build(hits, workspace_id=workspace_id)

    assert [c.text for c in package.chunks] == ["first", "second"]


async def test_entities_grouped_by_type() -> None:
    workspace_id = uuid.uuid4()
    person = _entity(
        workspace_id=workspace_id, entity_type="person", canonical_name="Alice"
    )
    org = _entity(
        workspace_id=workspace_id, entity_type="organization", canonical_name="Acme"
    )

    service = _service(entities=[person, org])
    hits = [_entity_hit(person), _entity_hit(org)]

    package = await service.build(hits, workspace_id=workspace_id)

    assert {e.canonical_name for e in package.entities_by_type["person"]} == {"Alice"}
    assert {e.canonical_name for e in package.entities_by_type["organization"]} == {
        "Acme"
    }


async def test_relationship_expansion_includes_only_resolved_entity_edges() -> None:
    workspace_id = uuid.uuid4()
    alice = _entity(workspace_id=workspace_id, canonical_name="Alice")
    bob = _entity(workspace_id=workspace_id, canonical_name="Bob")
    outsider = _entity(workspace_id=workspace_id, canonical_name="Outsider")
    connecting = _relationship(
        source_entity_id=alice.id, target_entity_id=bob.id, workspace_id=workspace_id
    )
    dangling = _relationship(
        source_entity_id=alice.id,
        target_entity_id=outsider.id,
        workspace_id=workspace_id,
    )

    service = _service(
        entities=[alice, bob, outsider], relationships=[connecting, dangling]
    )
    hits = [_entity_hit(alice), _entity_hit(bob)]

    package = await service.build(hits, workspace_id=workspace_id)

    assert len(package.relationships) == 1
    assert package.relationships[0].relationship_id == connecting.id


async def test_max_chunks_truncates_and_sets_flag() -> None:
    workspace_id = uuid.uuid4()
    document = _document()
    version = _version(document.id)
    chunks = [
        _chunk(document_version_id=version.id, chunk_index=i, text=f"chunk {i}")
        for i in range(3)
    ]
    service = _service(chunks=chunks, documents=[document], versions=[version])
    hits = [_chunk_hit(c, document_id=document.id) for c in chunks]

    package = await service.build(hits, workspace_id=workspace_id, max_chunks=1)

    assert len(package.chunks) == 1
    assert package.truncated is True


async def test_max_characters_truncates_chunk_text() -> None:
    workspace_id = uuid.uuid4()
    document = _document()
    version = _version(document.id)
    chunk = _chunk(document_version_id=version.id, text="x" * 100)
    service = _service(chunks=[chunk], documents=[document], versions=[version])
    hits = [_chunk_hit(chunk, document_id=document.id)]

    package = await service.build(hits, workspace_id=workspace_id, max_characters=10)

    assert len(package.chunks[0].text) == 10
    assert package.truncated is True


async def test_graph_depth_expands_neighbors_per_resolved_entity() -> None:
    workspace_id = uuid.uuid4()
    entity = _entity(workspace_id=workspace_id)
    neighbor_payload = [{"id": str(uuid.uuid4()), "canonical_name": "Neighbor"}]
    graph = _FakeKnowledgeGraphService(
        neighbors_by_entity={entity.id: neighbor_payload}
    )

    service = _service(entities=[entity], graph=graph)
    hits = [_entity_hit(entity)]

    package = await service.build(hits, workspace_id=workspace_id, graph_depth=2)

    assert graph.calls[0]["depth"] == 2
    assert package.graph_neighbors[str(entity.id)] == neighbor_payload


async def test_graph_neighbors_empty_when_graph_depth_zero() -> None:
    workspace_id = uuid.uuid4()
    entity = _entity(workspace_id=workspace_id)
    service = _service(entities=[entity])
    hits = [_entity_hit(entity)]

    package = await service.build(hits, workspace_id=workspace_id, graph_depth=0)

    assert package.graph_neighbors == {}


async def test_include_version_history_resolves_all_versions() -> None:
    workspace_id = uuid.uuid4()
    document = _document()
    v1 = _version(document.id, version_number=1, is_current=False)
    v2 = _version(document.id, version_number=2, is_current=True)
    chunk = _chunk(document_version_id=v2.id)
    service = _service(chunks=[chunk], documents=[document], versions=[v1, v2])
    hits = [_chunk_hit(chunk, document_id=document.id)]

    package = await service.build(
        hits, workspace_id=workspace_id, include_version_history=True
    )

    version_numbers = sorted(e.version_number for e in package.version_history)
    assert version_numbers == [1, 2]


async def test_deleted_entity_reference_is_skipped_not_raised() -> None:
    workspace_id = uuid.uuid4()
    deleted = _entity(workspace_id=workspace_id, is_deleted=True)
    service = _service(entities=[deleted])
    hits = [_entity_hit(deleted)]

    package = await service.build(hits, workspace_id=workspace_id)

    assert package.entities == []


async def test_build_publishes_context_built_event() -> None:
    events = EventDispatcher()
    received: list[ContextBuiltEvent] = []
    events.subscribe(ContextBuiltEvent, received.append)
    workspace_id = uuid.uuid4()
    entity = _entity(workspace_id=workspace_id)
    service = _service(entities=[entity], events=events)
    hits = [_entity_hit(entity)]

    await service.build(hits, workspace_id=workspace_id)

    assert len(received) == 1
    assert received[0].workspace_id == workspace_id
    assert received[0].entity_count == 1
