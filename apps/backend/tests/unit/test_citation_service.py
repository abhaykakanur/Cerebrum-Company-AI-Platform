"""Proves CIS Phase 3 Prompt 3's ``CitationService`` (Citation Engine):
resolving a raw ``Citation`` into an ``EnrichedCitation`` with human-
readable document/version/chunk/entity labels, deduplication across
hits that cite the same source, graceful handling of an unresolvable
entity reference, and ``CitationGeneratedEvent`` publication — against
hand-written fakes for every PostgreSQL repository (real Postgres is
unreachable in this sandbox — see cerebrum.application.semantic's test
precedents).
"""

import uuid
from datetime import UTC, datetime

import pytest

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.retrieval.citation_service import CitationService
from cerebrum.application.retrieval.events import CitationGeneratedEvent
from cerebrum.application.semantic.hybrid_search_service import Citation, SearchHit
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk
from cerebrum.infrastructure.database.models.document import Document
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.database.models.entity import Entity

pytestmark = pytest.mark.unit


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


def _document(name: str = "Report.pdf") -> Document:
    return Document(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        folder_id=None,
        name=name,
        status="active",
        current_version_id=None,
        created_at=datetime.now(UTC),
    )


def _version(document_id: uuid.UUID, version_number: int = 3) -> DocumentVersion:
    return DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        version_number=version_number,
        is_current=True,
    )


def _chunk(document_version_id: uuid.UUID, chunk_index: int = 5) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        document_version_id=document_version_id,
        extraction_id=uuid.uuid4(),
        strategy="paragraph",
        chunk_index=chunk_index,
        text="text",
        character_count=4,
        start_offset=0,
        end_offset=4,
        overlap_with_previous=0,
        chunk_metadata={},
        created_at=datetime.now(UTC),
    )


def _entity(workspace_id: uuid.UUID, canonical_name: str = "Acme Corp") -> Entity:
    return Entity(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        organization_id=uuid.uuid4(),
        entity_type="organization",
        canonical_name=canonical_name,
        aliases=[],
        description=None,
        confidence=0.8,
        provenance=[],
        created_at=datetime.now(UTC),
    )


def _hit(citation: Citation, source_id: str = "s1") -> SearchHit:
    return SearchHit(
        source_id=source_id,
        kind="chunk",
        title="Title",
        snippet="Snippet",
        fused_score=0.5,
        vector_score=0.5,
        keyword_score=None,
        citation=citation,
    )


def _service(
    *,
    documents: list[Document] | None = None,
    versions: list[DocumentVersion] | None = None,
    chunks: list[Chunk] | None = None,
    entities: list[Entity] | None = None,
    events: EventDispatcher | None = None,
) -> CitationService:
    return CitationService(
        document_repository=_FakeDocumentRepository(documents),  # type: ignore[arg-type]
        version_repository=_FakeDocumentVersionRepository(versions),  # type: ignore[arg-type]
        chunk_repository=_FakeChunkRepository(chunks),  # type: ignore[arg-type]
        entity_service=EntityService(
            entity_repository=_FakeEntityRepository(entities)  # type: ignore[arg-type]
        ),
        event_dispatcher=events or EventDispatcher(),
    )


async def test_enriches_document_version_chunk_and_entity_names() -> None:
    workspace_id = uuid.uuid4()
    document = _document(name="Handbook.pdf")
    version = _version(document.id, version_number=7)
    chunk = _chunk(version.id, chunk_index=12)
    entity = _entity(workspace_id, canonical_name="Acme Corp")
    citation = Citation(
        document_id=document.id,
        document_version_id=version.id,
        chunk_id=chunk.id,
        entity_id=entity.id,
        confidence=0.77,
        provenance={"index": "qdrant"},
    )
    service = _service(
        documents=[document], versions=[version], chunks=[chunk], entities=[entity]
    )

    citations = await service.build_citations(
        [_hit(citation)], workspace_id=workspace_id
    )

    assert len(citations) == 1
    enriched = citations[0]
    assert enriched.document_name == "Handbook.pdf"
    assert enriched.version_number == 7
    assert enriched.chunk_index == 12
    assert enriched.entity_name == "Acme Corp"
    assert enriched.confidence == 0.77
    assert enriched.provenance == {"index": "qdrant"}


async def test_deduplicates_citations_referencing_the_same_source() -> None:
    citation = Citation(
        document_id=uuid.uuid4(),
        document_version_id=None,
        chunk_id=None,
        entity_id=None,
        confidence=0.5,
        provenance={},
    )
    service = _service()
    hits = [_hit(citation, "s1"), _hit(citation, "s2")]

    citations = await service.build_citations(hits, workspace_id=uuid.uuid4())

    assert len(citations) == 1


async def test_missing_references_resolve_to_none_labels() -> None:
    citation = Citation(
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        entity_id=None,
        confidence=0.5,
        provenance={},
    )
    service = _service()

    citations = await service.build_citations(
        [_hit(citation)], workspace_id=uuid.uuid4()
    )

    enriched = citations[0]
    assert enriched.document_name is None
    assert enriched.version_number is None
    assert enriched.chunk_index is None


async def test_deleted_entity_reference_yields_none_entity_name() -> None:
    workspace_id = uuid.uuid4()
    deleted_id = uuid.uuid4()
    citation = Citation(
        document_id=None,
        document_version_id=None,
        chunk_id=None,
        entity_id=deleted_id,
        confidence=0.5,
        provenance={},
    )
    service = _service()

    citations = await service.build_citations(
        [_hit(citation)], workspace_id=workspace_id
    )

    assert citations[0].entity_name is None


async def test_build_citations_publishes_event() -> None:
    events = EventDispatcher()
    received: list[CitationGeneratedEvent] = []
    events.subscribe(CitationGeneratedEvent, received.append)
    service = _service(events=events)
    workspace_id = uuid.uuid4()
    citation = Citation(
        document_id=None,
        document_version_id=None,
        chunk_id=None,
        entity_id=None,
        confidence=1.0,
        provenance={},
    )

    await service.build_citations([_hit(citation)], workspace_id=workspace_id)

    assert len(received) == 1
    assert received[0].workspace_id == workspace_id
    assert received[0].citation_count == 1
