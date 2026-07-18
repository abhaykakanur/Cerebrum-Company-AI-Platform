"""Proves CIS Phase 2 Prompt 2's Background Processing framework
acceptance criterion "Background jobs enqueue correctly", plus Retry,
Cancellation, and tenant isolation — against a fake in-memory
:class:`~cerebrum.workers.queue.Queue`, the same fake-over-real-infra
pattern test_upload_service.py uses for MinIO.
"""

import uuid
from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.processing_service import ProcessingService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
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
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException
from cerebrum.workers.base import Job

pytestmark = pytest.mark.unit


class _FakeQueue:
    def __init__(self) -> None:
        self.items: list[Job[uuid.UUID]] = []

    async def enqueue(self, job: Job[uuid.UUID]) -> None:
        self.items.append(job)

    async def dequeue(self) -> Job[uuid.UUID] | None:
        return self.items.pop(0) if self.items else None

    async def size(self) -> int:
        return len(self.items)


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


def _processing_service(session: AsyncSession, queue: _FakeQueue) -> ProcessingService:
    return ProcessingService(
        job_repository=ProcessingJobRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        queue=queue,  # type: ignore[arg-type]
    )


async def _seed_document_with_version(
    session: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> uuid.UUID:
    from datetime import datetime

    from cerebrum.infrastructure.database.models.document_version import VersionType

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
        workspace_id=workspace_id, folder_id=None, name="Doc.pdf", created_by=user_id
    )
    await session.commit()
    version = await versions.create_version(
        document.id,
        workspace_id=workspace_id,
        version_type=VersionType.MAJOR,
        change_summary=None,
        mime_type="application/pdf",
        file_size_bytes=10,
        sha256_checksum="a" * 64,
        storage_path="p",
        original_filename="Doc.pdf",
        uploaded_filename="doc.pdf",
        uploaded_at=datetime.now(UTC),
        created_by=user_id,
    )
    await session.commit()
    return version.id


async def test_enqueue_creates_a_job_and_pushes_to_the_queue(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session, workspace_id=ws_id, user_id=user_id
    )
    queue = _FakeQueue()
    processing = _processing_service(db_session, queue)

    job = await processing.enqueue(
        version_id, workspace_id=ws_id, job_type=ProcessingJobType.PARSING
    )
    await db_session.commit()

    assert job.status == ProcessingJobStatus.PENDING.value
    assert len(queue.items) == 1
    assert queue.items[0].payload == job.id


async def test_enqueue_rejects_a_version_from_another_workspace(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session, workspace_id=ws_id, user_id=user_id
    )

    other_org = Organization(name="Other", slug="other")
    db_session.add(other_org)
    await db_session.flush()
    other_ws = Workspace(organization_id=other_org.id, name="Other", slug="other-ws")
    db_session.add(other_ws)
    await db_session.commit()

    processing = _processing_service(db_session, _FakeQueue())

    with pytest.raises(NotFoundException):
        await processing.enqueue(
            version_id, workspace_id=other_ws.id, job_type=ProcessingJobType.OCR
        )


async def test_retry_requires_a_failed_or_cancelled_job(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session, workspace_id=ws_id, user_id=user_id
    )
    processing = _processing_service(db_session, _FakeQueue())
    job = await processing.enqueue(
        version_id, workspace_id=ws_id, job_type=ProcessingJobType.CHUNKING
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await processing.retry(job.id, workspace_id=ws_id)  # still PENDING


async def test_retry_re_enqueues_a_failed_job(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session, workspace_id=ws_id, user_id=user_id
    )
    queue = _FakeQueue()
    processing = _processing_service(db_session, queue)
    job = await processing.enqueue(
        version_id, workspace_id=ws_id, job_type=ProcessingJobType.EMBEDDINGS
    )
    await db_session.commit()
    job.status = ProcessingJobStatus.FAILED.value
    await ProcessingJobRepository(db_session).update(job)
    await db_session.commit()
    queue.items.clear()

    retried = await processing.retry(job.id, workspace_id=ws_id)
    await db_session.commit()

    assert retried.status == ProcessingJobStatus.PENDING.value
    assert retried.retry_count == 1
    assert len(queue.items) == 1


async def test_retry_exhausts_after_max_retries(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session, workspace_id=ws_id, user_id=user_id
    )
    processing = _processing_service(db_session, _FakeQueue())
    job = await processing.enqueue(
        version_id, workspace_id=ws_id, job_type=ProcessingJobType.OCR
    )
    await db_session.commit()
    job.status = ProcessingJobStatus.FAILED.value
    job.retry_count = job.max_retries
    await ProcessingJobRepository(db_session).update(job)
    await db_session.commit()

    with pytest.raises(ValidationException):
        await processing.retry(job.id, workspace_id=ws_id)


async def test_cancel_requires_pending_or_running(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session, workspace_id=ws_id, user_id=user_id
    )
    processing = _processing_service(db_session, _FakeQueue())
    job = await processing.enqueue(
        version_id, workspace_id=ws_id, job_type=ProcessingJobType.PARSING
    )
    await db_session.commit()

    cancelled = await processing.cancel(job.id, workspace_id=ws_id)
    await db_session.commit()
    assert cancelled.status == ProcessingJobStatus.CANCELLED.value

    with pytest.raises(ValidationException):
        await processing.cancel(job.id, workspace_id=ws_id)  # already cancelled
