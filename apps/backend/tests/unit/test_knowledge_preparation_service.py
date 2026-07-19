"""Proves CIS Phase 2 Prompt 4's Processing Orchestration: the full
Extraction-then-Chunking pipeline, manifest statistics, aggregate
progress, resuming after a mid-pipeline failure without re-running a
completed stage, cancel, and event emission — the
``DocumentKnowledgePreparedEvent`` a future Phase 3 consumer would
subscribe to.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.chunking_service import ChunkingService
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.events import DocumentKnowledgePreparedEvent
from cerebrum.application.knowledge.extraction_service import ExtractionService
from cerebrum.application.knowledge.knowledge_preparation_service import (
    KnowledgePreparationService,
)
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.semantic.embedding_service import EmbeddingService
from cerebrum.application.semantic.search_service import SearchService
from cerebrum.application.semantic.vector_index_service import VectorIndexService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import ChunkingStrategy
from cerebrum.infrastructure.database.models.document_manifest import ManifestStatus
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import ProcessingJobStatus
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.embeddings.providers import HashingEmbeddingProvider
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
from cerebrum.repositories.postgres.document_manifest_repository import (
    DocumentManifestRepository,
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
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


class _FakeGraphRepository:
    """Stands in for
    cerebrum.repositories.neo4j.knowledge_graph_repository.KnowledgeGraphRepository
    — real Neo4j is unreachable in this sandbox (same reasoning as
    test_upload_service.py's ``_FakeUploader`` for MinIO).
    """

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
            "workspace_id": workspace_id,
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
            if node["workspace_id"] == workspace_id and not node["is_deleted"]
        )
        relationship_count = sum(
            1 for edge in self.edges.values() if not edge["is_deleted"]
        )
        return {"entity_count": entity_count, "relationship_count": relationship_count}

    async def validate_consistency(self, workspace_id) -> list:
        return []


def _graph_service(
    session: AsyncSession, *, events: EventDispatcher, graph_repository=None
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        relationship_service=RelationshipService(
            relationship_repository=RelationshipRepository(session)
        ),
        graph_repository=graph_repository or _FakeGraphRepository(),
        chunk_repository=ChunkRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        entity_extractor=CompositeEntityExtractor([RegexEntityExtractor()]),
        relationship_extractor=CueBasedRelationshipExtractor(),
        event_dispatcher=events,
    )


class _FakeVectorRepository:
    """Stands in for
    cerebrum.repositories.qdrant.vector_repository.VectorRepository —
    real Qdrant is unreachable in this sandbox.
    """

    def __init__(self) -> None:
        self.points: dict = {}

    async def ensure_collection(self) -> None:
        pass

    async def upsert_point(self, *, kind, source_id, vector, **payload_fields):
        point_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{kind}:{source_id}")
        self.points[point_id] = {
            "id": str(point_id),
            "payload": {"kind": kind, "source_id": str(source_id), **payload_fields},
        }
        return point_id

    async def get_point(self, kind, source_id):
        point_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{kind}:{source_id}")
        return self.points.get(point_id)

    async def delete_by_document_version(self, document_version_id) -> None:
        self.points = {
            pid: p
            for pid, p in self.points.items()
            if p["payload"].get("document_version_id") != str(document_version_id)
        }

    async def search(self, **kwargs) -> list:
        return []

    async def get_statistics(self, workspace_id) -> dict:
        return {"vector_count": len(self.points)}


class _FakeSearchIndexRepository:
    """Stands in for
    cerebrum.repositories.opensearch.search_index_repository.SearchIndexRepository
    — real OpenSearch is unreachable in this sandbox.
    """

    def __init__(self) -> None:
        self.documents: dict = {}

    async def ensure_index(self) -> None:
        pass

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
        return []


def _embedding_service(
    session: AsyncSession,
    *,
    events: EventDispatcher,
    vector_repository: _FakeVectorRepository | None = None,
) -> EmbeddingService:
    return EmbeddingService(
        provider=HashingEmbeddingProvider(dimension=32),
        vector_index_service=VectorIndexService(
            vector_repository=vector_repository or _FakeVectorRepository()
        ),
        chunk_repository=ChunkRepository(session),
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        relationship_service=RelationshipService(
            relationship_repository=RelationshipRepository(session)
        ),
        extraction_repository=DocumentExtractionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        job_repository=ProcessingJobRepository(session),
        event_dispatcher=events,
    )


def _search_service(
    session: AsyncSession,
    *,
    events: EventDispatcher,
    search_index_repository: _FakeSearchIndexRepository | None = None,
) -> SearchService:
    return SearchService(
        search_index_repository=search_index_repository or _FakeSearchIndexRepository(),
        event_dispatcher=events,
    )


class _FakeDownloader:
    def __init__(self, content_by_key: dict[str, bytes]) -> None:
        self._content_by_key = content_by_key

    async def download(self, *, object_key: str):
        yield self._content_by_key[object_key]

    async def presigned_download_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        return f"https://fake.example/{object_key}"


class _AlwaysBrokenDownloader:
    async def download(self, *, object_key: str):
        raise RuntimeError("storage unreachable")
        yield b""  # pragma: no cover

    async def presigned_download_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        raise RuntimeError("storage unreachable")


def _preparation_service(
    session: AsyncSession, downloader, *, events: EventDispatcher | None = None
) -> KnowledgePreparationService:
    event_dispatcher = events or EventDispatcher()
    return KnowledgePreparationService(
        extraction_service=ExtractionService(
            extraction_repository=DocumentExtractionRepository(session),
            metadata_repository=DocumentMetadataRepository(session),
            version_repository=DocumentVersionRepository(session),
            document_repository=DocumentRepository(session),
            job_repository=ProcessingJobRepository(session),
            downloader=downloader,
        ),
        chunking_service=ChunkingService(
            chunk_repository=ChunkRepository(session),
            extraction_repository=DocumentExtractionRepository(session),
            version_repository=DocumentVersionRepository(session),
            document_repository=DocumentRepository(session),
            job_repository=ProcessingJobRepository(session),
        ),
        graph_service=_graph_service(session, events=event_dispatcher),
        embedding_service=_embedding_service(session, events=event_dispatcher),
        search_service=_search_service(session, events=event_dispatcher),
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        manifest_repository=DocumentManifestRepository(session),
        extraction_repository=DocumentExtractionRepository(session),
        job_repository=ProcessingJobRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        event_dispatcher=event_dispatcher,
    )


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    org = Organization(name="Acme", slug="acme")
    session.add(org)
    await session.flush()
    ws = Workspace(organization_id=org.id, name="Default", slug="default")
    session.add(ws)
    user = User(
        organization_id=org.id,
        email="alice@example.com",
        hashed_password="x",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return ws.id, user.id


async def _seed_version(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    storage_path: str,
) -> uuid.UUID:
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
        workspace_id=workspace_id, folder_id=None, name="Doc", created_by=user_id
    )
    await session.commit()
    version = await versions.create_version(
        document.id,
        workspace_id=workspace_id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="text/plain",
        file_size_bytes=10,
        sha256_checksum="a" * 64,
        storage_path=storage_path,
        original_filename="doc",
        uploaded_filename="doc",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await session.commit()
    return version.id


async def test_prepare_runs_extraction_then_chunking_and_builds_a_ready_manifest(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(
        db_session, workspace_id=ws_id, user_id=user_id, storage_path="ws/doc/key.txt"
    )
    downloader = _FakeDownloader(
        {"ws/doc/key.txt": b"First paragraph.\n\nSecond paragraph."}
    )
    events = EventDispatcher()
    received: list[DocumentKnowledgePreparedEvent] = []
    events.subscribe(DocumentKnowledgePreparedEvent, received.append)
    service = _preparation_service(db_session, downloader, events=events)

    manifest = await service.prepare(
        version_id, workspace_id=ws_id, strategy=ChunkingStrategy.PARAGRAPH
    )
    await db_session.commit()

    assert manifest.status == ManifestStatus.READY.value
    assert manifest.chunk_count == 2
    assert manifest.chunking_strategy == ChunkingStrategy.PARAGRAPH.value
    assert manifest.total_character_count > 0
    assert manifest.statistics["avg_chunk_size"] > 0

    assert len(received) == 1
    assert received[0].document_version_id == version_id
    assert received[0].chunk_count == 2


async def test_prepare_does_not_re_extract_a_completed_extraction_unless_forced(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(
        db_session, workspace_id=ws_id, user_id=user_id, storage_path="ws/doc/key.txt"
    )
    downloader = _FakeDownloader({"ws/doc/key.txt": b"hello world"})
    service = _preparation_service(db_session, downloader)

    first = await service.prepare(version_id, workspace_id=ws_id)
    await db_session.commit()

    # Second call with a broken downloader: if it tried to re-extract,
    # this would fail — proves it skipped straight to chunking.
    broken_service = _preparation_service(db_session, _AlwaysBrokenDownloader())
    second = await broken_service.prepare(
        version_id, workspace_id=ws_id, strategy=ChunkingStrategy.SENTENCE
    )
    await db_session.commit()

    assert second.status == ManifestStatus.READY.value
    assert second.extraction_id == first.extraction_id


async def test_prepare_reports_failure_when_extraction_fails(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(
        db_session, workspace_id=ws_id, user_id=user_id, storage_path="ws/doc/key.txt"
    )
    service = _preparation_service(db_session, _AlwaysBrokenDownloader())

    manifest = await service.prepare(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert manifest.status == ManifestStatus.FAILED.value
    assert manifest.chunk_count == 0
    assert manifest.error_message is not None


async def test_get_progress_averages_both_stages(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(
        db_session, workspace_id=ws_id, user_id=user_id, storage_path="ws/doc/key.txt"
    )
    downloader = _FakeDownloader({"ws/doc/key.txt": b"hello world"})
    service = _preparation_service(db_session, downloader)

    await service.prepare(version_id, workspace_id=ws_id)
    await db_session.commit()

    progress = await service.get_progress(version_id, workspace_id=ws_id)

    assert progress.extraction_status == ProcessingJobStatus.COMPLETED.value
    assert progress.chunking_status == ProcessingJobStatus.COMPLETED.value
    assert progress.overall_progress_percent == 100


async def test_get_manifest_requires_a_prior_prepare_call(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(
        db_session, workspace_id=ws_id, user_id=user_id, storage_path="ws/doc/key.txt"
    )
    service = _preparation_service(db_session, _FakeDownloader({}))

    with pytest.raises(NotFoundException):
        await service.get_manifest(version_id, workspace_id=ws_id)


async def test_cancel_stops_a_pending_job_created_via_raw_enqueue(
    db_session: AsyncSession,
) -> None:
    from cerebrum.application.knowledge.processing_service import ProcessingService
    from cerebrum.infrastructure.database.models.processing_job import ProcessingJobType

    class _FakeQueue:
        async def enqueue(self, job) -> None:
            pass

    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_version(
        db_session, workspace_id=ws_id, user_id=user_id, storage_path="ws/doc/key.txt"
    )
    processing = ProcessingService(
        job_repository=ProcessingJobRepository(db_session),
        version_repository=DocumentVersionRepository(db_session),
        document_repository=DocumentRepository(db_session),
        queue=_FakeQueue(),
    )
    job = await processing.enqueue(
        version_id, workspace_id=ws_id, job_type=ProcessingJobType.EMBEDDINGS
    )
    await db_session.commit()
    assert job.status == ProcessingJobStatus.PENDING.value

    service = _preparation_service(db_session, _FakeDownloader({}))
    cancelled_count = await service.cancel(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert cancelled_count == 1
    refreshed = await ProcessingJobRepository(db_session).get_by_id(job.id)
    assert refreshed is not None
    assert refreshed.status == ProcessingJobStatus.CANCELLED.value
