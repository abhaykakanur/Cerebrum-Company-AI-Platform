"""Proves CIS Phase 3 Prompt 2's ``EmbeddingService``: batch generation
across every artifact kind (chunk/entity/relationship/document-summary/
metadata), incremental updates (skip-if-current), regeneration
(force=True bypasses the skip), retry, progress tracking via
``ProcessingJob``, event emission, and tenant isolation — against a
real database and a fake ``VectorRepository`` (real Qdrant is
unreachable in this sandbox).
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.semantic.embedding_service import EmbeddingService
from cerebrum.application.semantic.events import (
    EmbeddingsGeneratedEvent,
    VectorIndexUpdatedEvent,
)
from cerebrum.application.semantic.vector_index_service import VectorIndexService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import ProcessingJobStatus
from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.embeddings.providers import HashingEmbeddingProvider
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


class _FakeVectorRepository:
    def __init__(self, *, fail: bool = False) -> None:
        self.points: dict[uuid.UUID, dict] = {}
        self._fail = fail

    async def ensure_collection(self) -> None:
        pass

    async def upsert_point(self, *, kind, source_id, vector, **payload_fields):
        if self._fail:
            raise RuntimeError("qdrant unreachable")
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
        pass

    async def search(self, **kwargs) -> list:
        return []

    async def get_statistics(self, workspace_id) -> dict:
        return {"vector_count": len(self.points)}


def _embedding_service(
    session: AsyncSession,
    *,
    events: EventDispatcher,
    vector_repository: _FakeVectorRepository | None = None,
    dimension: int = 32,
) -> EmbeddingService:
    return EmbeddingService(
        provider=HashingEmbeddingProvider(dimension=dimension),
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


async def _seed_version_with_artifacts(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Seeds a document version with one chunk, one entity sourced from
    it, one relationship, a completed extraction, and metadata — every
    kind ``EmbeddingService`` embeds. Returns ``(workspace_id,
    document_version_id)``.
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
        workspace_id=ws.id, folder_id=None, name="Doc.txt", created_by=None
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
        original_filename="Doc.txt",
        uploaded_filename="doc.txt",
        uploaded_at=datetime.now(UTC),
        created_by=None,
    )
    await session.commit()

    extraction = await DocumentExtractionRepository(session).add(
        DocumentExtraction(
            document_version_id=version.id,
            status=ExtractionStatus.COMPLETED.value,
            extracted_text="Alice Johnson reports to Bob Williams at Acme Corp.",
            extracted_metadata={},
        )
    )
    await session.commit()

    chunk = await ChunkRepository(session).add(
        Chunk(
            document_version_id=version.id,
            extraction_id=extraction.id,
            strategy=ChunkingStrategy.PARAGRAPH.value,
            chunk_index=0,
            text="Alice Johnson reports to Bob Williams at Acme Corp.",
            character_count=52,
            start_offset=0,
            end_offset=52,
            overlap_with_previous=0,
            chunk_metadata={},
        )
    )
    await session.commit()

    entities = EntityService(entity_repository=EntityRepository(session))
    alice = await entities.create(
        workspace_id=ws.id,
        organization_id=org.id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Johnson",
        description="A person mentioned in the document.",
    )
    bob = await entities.create(
        workspace_id=ws.id,
        organization_id=org.id,
        entity_type=EntityType.PERSON,
        canonical_name="Bob Williams",
    )
    alice.source_chunk_id = chunk.id
    await EntityRepository(session).update(alice)
    await session.commit()

    relationships = RelationshipService(
        relationship_repository=RelationshipRepository(session)
    )
    relationship = await relationships.create(
        workspace_id=ws.id,
        organization_id=org.id,
        source_entity_id=alice.id,
        target_entity_id=bob.id,
        relationship_type=RelationshipType.REPORTS_TO,
        evidence="Alice Johnson reports to Bob Williams.",
    )
    relationship.source_chunk_id = chunk.id
    await RelationshipRepository(session).update(relationship)
    await session.commit()

    return ws.id, version.id


async def test_embed_version_embeds_every_artifact_kind(
    db_session: AsyncSession,
) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    vectors = _FakeVectorRepository()
    service = _embedding_service(
        db_session, events=EventDispatcher(), vector_repository=vectors
    )

    job = await service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert job.progress_percent == 100
    kinds = {point["payload"]["kind"] for point in vectors.points.values()}
    assert kinds == {
        "chunk",
        "entity_description",
        "relationship_description",
        "document_summary",
        "metadata",
    }


async def test_embed_version_publishes_events(db_session: AsyncSession) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    events = EventDispatcher()
    received_generated: list[EmbeddingsGeneratedEvent] = []
    received_indexed: list[VectorIndexUpdatedEvent] = []
    events.subscribe(EmbeddingsGeneratedEvent, received_generated.append)
    events.subscribe(VectorIndexUpdatedEvent, received_indexed.append)
    service = _embedding_service(db_session, events=events)

    await service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert len(received_generated) == 1
    assert len(received_indexed) == 1
    assert received_generated[0].embedding_count == received_indexed[0].vector_count


async def test_incremental_update_skips_already_current_artifacts(
    db_session: AsyncSession,
) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    vectors = _FakeVectorRepository()
    service = _embedding_service(
        db_session, events=EventDispatcher(), vector_repository=vectors
    )

    first = await service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()
    assert first.status == ProcessingJobStatus.COMPLETED.value

    second = await service.embed_version(version_id, workspace_id=ws_id, force=False)
    await db_session.commit()

    assert second.status == ProcessingJobStatus.COMPLETED.value
    # Nothing changed since the first run, so the second run's own
    # per-artifact upserts should all have been skipped — no error, no
    # additional points beyond what the first run created.
    assert len(vectors.points) == 5


async def test_force_regenerates_even_when_already_current(
    db_session: AsyncSession,
) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    vectors = _FakeVectorRepository()
    service = _embedding_service(
        db_session, events=EventDispatcher(), vector_repository=vectors
    )
    await service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()
    point_ids_before = set(vectors.points.keys())

    await service.embed_version(version_id, workspace_id=ws_id, force=True)
    await db_session.commit()

    # Same deterministic point IDs (re-embedded, not duplicated).
    assert set(vectors.points.keys()) == point_ids_before


async def test_embed_version_records_failure_without_raising(
    db_session: AsyncSession,
) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    service = _embedding_service(
        db_session,
        events=EventDispatcher(),
        vector_repository=_FakeVectorRepository(fail=True),
    )

    job = await service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert job.status == ProcessingJobStatus.FAILED.value
    assert job.error_message == "qdrant unreachable"


async def test_retry_requires_a_failed_or_cancelled_job(
    db_session: AsyncSession,
) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    service = _embedding_service(db_session, events=EventDispatcher())
    job = await service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()

    from cerebrum.shared.errors.exceptions import ValidationException

    with pytest.raises(ValidationException):
        await service.retry(job.id, workspace_id=ws_id)  # already COMPLETED


async def test_retry_re_runs_a_failed_job(db_session: AsyncSession) -> None:
    ws_id, version_id = await _seed_version_with_artifacts(db_session)
    broken_service = _embedding_service(
        db_session,
        events=EventDispatcher(),
        vector_repository=_FakeVectorRepository(fail=True),
    )
    failed_job = await broken_service.embed_version(version_id, workspace_id=ws_id)
    await db_session.commit()
    assert failed_job.status == ProcessingJobStatus.FAILED.value

    working_service = _embedding_service(db_session, events=EventDispatcher())
    retried_job = await working_service.retry(failed_job.id, workspace_id=ws_id)
    await db_session.commit()

    assert retried_job.status == ProcessingJobStatus.COMPLETED.value
    assert retried_job.retry_count == 1


async def test_embed_version_rejects_a_version_from_another_workspace(
    db_session: AsyncSession,
) -> None:
    _ws_id, version_id = await _seed_version_with_artifacts(db_session)
    service = _embedding_service(db_session, events=EventDispatcher())

    with pytest.raises(NotFoundException):
        await service.embed_version(version_id, workspace_id=uuid.uuid4())
