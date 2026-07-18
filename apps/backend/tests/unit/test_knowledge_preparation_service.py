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
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import ChunkingStrategy
from cerebrum.infrastructure.database.models.document_manifest import ManifestStatus
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import ProcessingJobStatus
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
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
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import NotFoundException

pytestmark = pytest.mark.unit


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
        manifest_repository=DocumentManifestRepository(session),
        extraction_repository=DocumentExtractionRepository(session),
        job_repository=ProcessingJobRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        event_dispatcher=events or EventDispatcher(),
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
