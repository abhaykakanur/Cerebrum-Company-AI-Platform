"""Proves CIS Phase 2 Prompt 3's Intelligent Document Processing
Pipeline end to end: dispatch by MIME type, real text extraction against
a fake ``FileDownloader`` standing in for MinIO (same fake-over-real-
infra pattern test_upload_service.py established), ProcessingJob
status/progress reflecting a real run, unsupported-format handling,
failure handling, retry re-execution, and tenant isolation.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.extraction_service import ExtractionService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.infrastructure.database.models.document_extraction import (
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
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
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

pytestmark = pytest.mark.unit


class _FakeDownloader:
    def __init__(self, content_by_key: dict[str, bytes]) -> None:
        self._content_by_key = content_by_key

    async def download(self, *, object_key: str) -> AsyncIterator[bytes]:
        yield self._content_by_key[object_key]

    async def presigned_download_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        return f"https://fake.example/{object_key}"


class _AlwaysBrokenDownloader:
    async def download(self, *, object_key: str) -> AsyncIterator[bytes]:
        raise RuntimeError("storage unreachable")
        yield b""  # pragma: no cover - unreachable, satisfies generator typing

    async def presigned_download_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        raise RuntimeError("storage unreachable")


def _extraction_service(session: AsyncSession, downloader) -> ExtractionService:
    return ExtractionService(
        extraction_repository=DocumentExtractionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        job_repository=ProcessingJobRepository(session),
        downloader=downloader,
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


async def _seed_document_with_version(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    mime_type: str,
    storage_path: str,
) -> uuid.UUID:
    from datetime import datetime

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
        mime_type=mime_type,
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


async def test_extract_runs_the_matching_parser_and_completes_the_job(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="text/plain",
        storage_path="ws/doc/key.txt",
    )
    downloader = _FakeDownloader({"ws/doc/key.txt": b"hello extracted world"})
    service = _extraction_service(db_session, downloader)

    result = await service.extract(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert result.status == ExtractionStatus.COMPLETED.value
    assert result.extracted_text == "hello extracted world"
    assert result.processing_job_id is not None

    job = await ProcessingJobRepository(db_session).get_by_id(result.processing_job_id)
    assert job is not None
    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert job.progress_percent == 100
    assert job.job_type == ProcessingJobType.PARSING.value


async def test_extract_dispatches_images_to_the_ocr_job_type(
    db_session: AsyncSession,
) -> None:
    import io

    from PIL import Image

    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="image/png",
        storage_path="ws/doc/photo.png",
    )
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    downloader = _FakeDownloader({"ws/doc/photo.png": buffer.getvalue()})
    service = _extraction_service(db_session, downloader)

    result = await service.extract(version_id, workspace_id=ws_id)
    await db_session.commit()

    job = await ProcessingJobRepository(db_session).get_by_id(result.processing_job_id)
    assert job is not None
    assert job.job_type == ProcessingJobType.OCR.value
    assert result.status == ExtractionStatus.COMPLETED.value


async def test_extract_marks_unsupported_formats_without_raising(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="application/x-proprietary-format",
        storage_path="ws/doc/key.bin",
    )
    downloader = _FakeDownloader({"ws/doc/key.bin": b"binary junk"})
    service = _extraction_service(db_session, downloader)

    result = await service.extract(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert result.status == ExtractionStatus.UNSUPPORTED_FORMAT.value
    assert result.extracted_text is None

    job = await ProcessingJobRepository(db_session).get_by_id(result.processing_job_id)
    assert job is not None
    assert job.status == ProcessingJobStatus.FAILED.value


async def test_extract_records_failure_when_storage_is_unreachable(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="text/plain",
        storage_path="ws/doc/key.txt",
    )
    service = _extraction_service(db_session, _AlwaysBrokenDownloader())

    result = await service.extract(version_id, workspace_id=ws_id)
    await db_session.commit()

    assert result.status == ExtractionStatus.FAILED.value
    assert result.error_message == "storage unreachable"

    job = await ProcessingJobRepository(db_session).get_by_id(result.processing_job_id)
    assert job is not None
    assert job.status == ProcessingJobStatus.FAILED.value
    assert job.error_message == "storage unreachable"


async def test_retry_re_runs_extraction_and_overwrites_the_previous_result(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="text/plain",
        storage_path="ws/doc/key.txt",
    )
    broken_then_working = _extraction_service(db_session, _AlwaysBrokenDownloader())
    failed = await broken_then_working.extract(version_id, workspace_id=ws_id)
    await db_session.commit()
    assert failed.status == ExtractionStatus.FAILED.value

    working_downloader = _FakeDownloader({"ws/doc/key.txt": b"recovered text"})
    service = _extraction_service(db_session, working_downloader)
    retried = await service.retry(failed.processing_job_id, workspace_id=ws_id)
    await db_session.commit()

    assert retried.id == failed.id  # same 1:1 extraction row, overwritten
    assert retried.status == ExtractionStatus.COMPLETED.value
    assert retried.extracted_text == "recovered text"

    job = await ProcessingJobRepository(db_session).get_by_id(failed.processing_job_id)
    assert job is not None
    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert job.retry_count == 1


async def test_retry_rejects_a_pending_job(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="text/plain",
        storage_path="ws/doc/key.txt",
    )
    downloader = _FakeDownloader({"ws/doc/key.txt": b"content"})
    service = _extraction_service(db_session, downloader)
    result = await service.extract(version_id, workspace_id=ws_id)
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.retry(result.processing_job_id, workspace_id=ws_id)


async def test_get_for_version_requires_a_prior_extraction(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="text/plain",
        storage_path="ws/doc/key.txt",
    )
    service = _extraction_service(db_session, _FakeDownloader({}))

    with pytest.raises(NotFoundException):
        await service.get_for_version(version_id, workspace_id=ws_id)


async def test_extract_rejects_a_version_from_another_workspace(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    version_id = await _seed_document_with_version(
        db_session,
        workspace_id=ws_id,
        user_id=user_id,
        mime_type="text/plain",
        storage_path="ws/doc/key.txt",
    )
    other_org = Organization(name="Other", slug="other")
    db_session.add(other_org)
    await db_session.flush()
    other_ws = Workspace(organization_id=other_org.id, name="Other", slug="other-ws")
    db_session.add(other_ws)
    await db_session.commit()

    service = _extraction_service(db_session, _FakeDownloader({}))

    with pytest.raises(NotFoundException):
        await service.extract(version_id, workspace_id=other_ws.id)
