"""Proves CIS Phase 3 Prompt 1's pipeline extension end to end: Chunk ->
Entity Extraction -> Relationship Extraction -> Graph Update, against a
real database and a fake Neo4j repository (real Neo4j is unreachable in
this sandbox — same reasoning as test_upload_service.py's
``_FakeUploader`` for MinIO). Covers entity/relationship persistence,
event emission, version-aware supersede on re-run, graph queries
(neighbors/statistics/consistency), and soft-delete propagation.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.events import (
    EntityExtractedEvent,
    GraphUpdatedEvent,
    RelationshipExtractedEvent,
)
from cerebrum.application.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.entities.extractors import (
    CompositeEntityExtractor,
    RegexEntityExtractor,
)
from cerebrum.infrastructure.relationships.extractors import (
    CueBasedRelationshipExtractor,
)
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_extraction_repository import (
    DocumentExtractionRepository,
)
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


class _FakeGraphRepository:
    def __init__(self) -> None:
        self.nodes: dict = {}
        self.edges: dict = {}

    async def upsert_entity_node(
        self,
        *,
        entity_id,
        workspace_id,
        entity_type,
        canonical_name,
        aliases,
        confidence,
    ) -> None:
        self.nodes[entity_id] = {
            "id": str(entity_id),
            "workspace_id": str(workspace_id),
            "entity_type": entity_type,
            "canonical_name": canonical_name,
            "aliases": aliases,
            "confidence": confidence,
            "is_deleted": False,
        }

    async def soft_delete_entity_node(self, entity_id) -> None:
        if entity_id in self.nodes:
            self.nodes[entity_id]["is_deleted"] = True

    async def upsert_relationship_edge(
        self,
        *,
        relationship_id,
        source_entity_id,
        target_entity_id,
        relationship_type,
        confidence,
    ) -> None:
        self.edges[relationship_id] = {
            "source": source_entity_id,
            "target": target_entity_id,
            "type": relationship_type,
            "confidence": confidence,
            "is_deleted": False,
        }

    async def soft_delete_relationship_edge(self, relationship_id) -> None:
        if relationship_id in self.edges:
            self.edges[relationship_id]["is_deleted"] = True

    async def get_neighbors(self, entity_id, *, depth: int = 1) -> list:
        neighbor_ids = set()
        for edge in self.edges.values():
            if edge["is_deleted"]:
                continue
            if edge["source"] == entity_id:
                neighbor_ids.add(edge["target"])
            elif edge["target"] == entity_id:
                neighbor_ids.add(edge["source"])
        return [
            self.nodes[nid]
            for nid in neighbor_ids
            if nid in self.nodes and not self.nodes[nid]["is_deleted"]
        ]

    async def get_statistics(self, workspace_id) -> dict:
        entity_count = sum(
            1
            for node in self.nodes.values()
            if node["workspace_id"] == str(workspace_id) and not node["is_deleted"]
        )
        relationship_count = sum(
            1 for edge in self.edges.values() if not edge["is_deleted"]
        )
        return {"entity_count": entity_count, "relationship_count": relationship_count}

    async def validate_consistency(self, workspace_id) -> list:
        return []


def _graph_service(
    session: AsyncSession,
    *,
    graph_repository: _FakeGraphRepository,
    events: EventDispatcher,
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        relationship_service=RelationshipService(
            relationship_repository=RelationshipRepository(session)
        ),
        graph_repository=graph_repository,
        chunk_repository=ChunkRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        entity_extractor=CompositeEntityExtractor([RegexEntityExtractor()]),
        relationship_extractor=CueBasedRelationshipExtractor(),
        event_dispatcher=events,
    )


async def _seed_version_with_chunks(
    session: AsyncSession, texts: list[str]
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, list[uuid.UUID]]:
    """Returns ``(workspace_id, organization_id, document_version_id,
    chunk_ids)``.
    """
    org = Organization(name="Acme", slug="acme")
    session.add(org)
    await session.flush()
    ws = Workspace(organization_id=org.id, name="Default", slug="default")
    session.add(ws)
    await session.commit()

    documents = DocumentService(
        document_repository=DocumentRepository(session),
        folder_repository=FolderRepository(session),
        tag_repository=TagRepository(session),
        label_repository=LabelRepository(session),
    )
    versions = VersionService(
        version_repository=DocumentVersionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        document_repository=DocumentRepository(session),
    )
    document = await documents.create(
        workspace_id=ws.id, folder_id=None, name="Doc", created_by=None
    )
    await session.commit()
    version = await versions.create_version(
        document.id,
        workspace_id=ws.id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="text/plain",
        file_size_bytes=10,
        sha256_checksum="a" * 64,
        storage_path="p",
        original_filename="doc",
        uploaded_filename="doc",
        uploaded_at=datetime.now(UTC),
        created_by=None,
    )
    await session.commit()

    extraction = await DocumentExtractionRepository(session).add(
        DocumentExtraction(
            document_version_id=version.id,
            status=ExtractionStatus.COMPLETED.value,
            extracted_text="\n\n".join(texts),
            extracted_metadata={},
        )
    )
    await session.commit()

    chunk_repo = ChunkRepository(session)
    chunk_ids = []
    for index, text in enumerate(texts):
        chunk = await chunk_repo.add(
            Chunk(
                document_version_id=version.id,
                extraction_id=extraction.id,
                strategy=ChunkingStrategy.PARAGRAPH.value,
                chunk_index=index,
                text=text,
                character_count=len(text),
                start_offset=0,
                end_offset=len(text),
                overlap_with_previous=0,
                chunk_metadata={},
            )
        )
        chunk_ids.append(chunk.id)
    await session.commit()
    return ws.id, org.id, version.id, chunk_ids


async def test_process_version_extracts_entities_and_relationships(
    db_session: AsyncSession,
) -> None:
    ws_id, _org_id, version_id, _chunk_ids = await _seed_version_with_chunks(
        db_session, ["Alice Johnson reports to Bob Williams."]
    )

    graph_repo = _FakeGraphRepository()
    events = EventDispatcher()
    received_graph_updates: list[GraphUpdatedEvent] = []
    received_entities: list[EntityExtractedEvent] = []
    received_relationships: list[RelationshipExtractedEvent] = []
    events.subscribe(GraphUpdatedEvent, received_graph_updates.append)
    events.subscribe(EntityExtractedEvent, received_entities.append)
    events.subscribe(RelationshipExtractedEvent, received_relationships.append)

    service = _graph_service(db_session, graph_repository=graph_repo, events=events)
    result = await service.process_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert result.entity_count >= 2  # Alice Johnson, Bob Williams
    assert result.relationship_count >= 1
    assert len(received_graph_updates) == 1
    assert received_graph_updates[0].entity_count == result.entity_count
    assert len(received_entities) == result.entity_count
    assert len(received_relationships) == result.relationship_count
    assert len(graph_repo.nodes) == result.entity_count
    assert len(graph_repo.edges) == result.relationship_count


async def test_process_version_rejects_a_version_from_another_workspace(
    db_session: AsyncSession,
) -> None:
    _ws_id, _org_id, version_id, _chunk_ids = await _seed_version_with_chunks(
        db_session, ["Alice Johnson reports to Bob Williams."]
    )
    service = _graph_service(
        db_session, graph_repository=_FakeGraphRepository(), events=EventDispatcher()
    )

    with pytest.raises(NotFoundException):
        await service.process_version(version_id, workspace_id=uuid.uuid4())


async def test_reprocessing_the_same_chunk_set_supersedes_the_prior_run(
    db_session: AsyncSession,
) -> None:
    ws_id, _org_id, version_id, _chunk_ids = await _seed_version_with_chunks(
        db_session, ["Alice Johnson reports to Bob Williams."]
    )
    graph_repo = _FakeGraphRepository()
    service = _graph_service(
        db_session, graph_repository=graph_repo, events=EventDispatcher()
    )

    first = await service.process_version(version_id, workspace_id=ws_id)
    await db_session.commit()
    first_entity_ids = set(graph_repo.nodes.keys())

    second = await service.process_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert second.entity_count == first.entity_count
    # Every node from the first run was soft-deleted, not left active
    # alongside the second run's fresh nodes.
    assert all(graph_repo.nodes[eid]["is_deleted"] for eid in first_entity_ids)
    active_nodes = [n for n in graph_repo.nodes.values() if not n["is_deleted"]]
    assert len(active_nodes) == second.entity_count


async def test_get_neighbors_delegates_to_the_graph_repository(
    db_session: AsyncSession,
) -> None:
    ws_id, _org_id, version_id, _chunk_ids = await _seed_version_with_chunks(
        db_session, ["Alice Johnson reports to Bob Williams."]
    )
    graph_repo = _FakeGraphRepository()
    service = _graph_service(
        db_session, graph_repository=graph_repo, events=EventDispatcher()
    )
    await service.process_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    alice_id = next(
        uuid.UUID(node["id"])
        for node in graph_repo.nodes.values()
        if node["canonical_name"] == "Alice Johnson"
    )
    neighbors = await service.get_neighbors(alice_id, workspace_id=ws_id)
    assert any(n["canonical_name"] == "Bob Williams" for n in neighbors)


async def test_get_statistics_and_validate_consistency(
    db_session: AsyncSession,
) -> None:
    ws_id, _org_id, version_id, _chunk_ids = await _seed_version_with_chunks(
        db_session, ["Alice Johnson reports to Bob Williams."]
    )
    graph_repo = _FakeGraphRepository()
    service = _graph_service(
        db_session, graph_repository=graph_repo, events=EventDispatcher()
    )
    result = await service.process_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    statistics = await service.get_statistics(workspace_id=ws_id)
    assert statistics["entity_count"] == result.entity_count
    assert statistics["relationship_count"] == result.relationship_count

    issues = await service.validate_consistency(workspace_id=ws_id)
    assert issues == []


async def test_soft_delete_entity_propagates_to_the_graph(
    db_session: AsyncSession,
) -> None:
    ws_id, _org_id, version_id, _chunk_ids = await _seed_version_with_chunks(
        db_session, ["Alice Johnson reports to Bob Williams."]
    )
    graph_repo = _FakeGraphRepository()
    service = _graph_service(
        db_session, graph_repository=graph_repo, events=EventDispatcher()
    )
    await service.process_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    entity_id = next(iter(graph_repo.nodes.keys()))
    await service.soft_delete_entity(entity_id, workspace_id=ws_id)
    await db_session.commit()

    assert graph_repo.nodes[entity_id]["is_deleted"] is True
    entities = EntityService(entity_repository=EntityRepository(db_session))
    with pytest.raises(NotFoundException):
        await entities.get(entity_id, workspace_id=ws_id)
