"""Proves CIS Phase 2 Prompt 2's Upload Pipeline acceptance criteria:
"Files upload successfully", "Metadata persists", "Files stored in
MinIO" (via a fake ``FileUploader`` standing in for the real MinIO
adapter — the same fake-over-real-infra pattern
test_rate_limiter.py/test_rate_limit_dependencies.py already established
for Redis), and "Validation works" (MIME type, size, duplicate checksum,
corrupted upload).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.upload_service import UploadService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.config.documents import DocumentSettings
from cerebrum.infrastructure.database.models.document_metadata import (
    QuarantineStatus,
)
from cerebrum.infrastructure.database.models.document_version import UploadStatus
from cerebrum.infrastructure.database.models.organization import Organization
from cerebrum.infrastructure.database.models.user import User
from cerebrum.infrastructure.database.models.workspace import Workspace
from cerebrum.infrastructure.security.virus_scan import NoOpVirusScanner, ScanResult
from cerebrum.infrastructure.storage.files import UploadedFile
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.shared.errors.exceptions import ConflictException, ValidationException

pytestmark = pytest.mark.unit


class _FakeUploader:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def upload(
        self, *, object_key: str, content: bytes, content_type: str, size_bytes: int
    ) -> UploadedFile:
        self.uploaded[object_key] = content
        return UploadedFile(
            object_key=object_key,
            filename=object_key.rsplit("/", 1)[-1],
            content_type=content_type,
            size_bytes=size_bytes,
        )

    async def delete(self, object_key: str) -> None:
        self.deleted.append(object_key)
        self.uploaded.pop(object_key, None)

    async def presigned_upload_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        return f"https://fake.example/{object_key}"


class _AlwaysQuarantineScanner:
    async def scan(self, content: bytes) -> ScanResult:
        return ScanResult(status=QuarantineStatus.QUARANTINED, detail="test fixture")


class _FakeAuditRepository:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def add(self, entity):  # type: ignore[no-untyped-def]
        self.events.append(entity)
        return entity


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


class _FakeKnowledgePreparationService:
    async def prepare(self, *args, **kwargs):
        return None


def _upload_service(
    session: AsyncSession,
    uploader: _FakeUploader,
    *,
    scanner=None,
    max_size=1024,
    allowed_mime=None,
    audit_repository: _FakeAuditRepository | None = None,
) -> UploadService:
    return UploadService(
        version_service=VersionService(
            version_repository=DocumentVersionRepository(session),
            metadata_repository=DocumentMetadataRepository(session),
            document_repository=DocumentRepository(session),
        ),
        document_repository=DocumentRepository(session),
        uploader=uploader,  # type: ignore[arg-type]
        virus_scanner=scanner or NoOpVirusScanner(),
        settings=DocumentSettings(
            max_file_size_bytes=max_size, allowed_mime_types=allowed_mime or []
        ),
        audit_service=AuditService(audit_repository or _FakeAuditRepository()),  # type: ignore[arg-type]
        preparation_service=_FakeKnowledgePreparationService(),  # type: ignore[arg-type]
    )


def _document_service(session: AsyncSession) -> DocumentService:
    return DocumentService(
        document_repository=DocumentRepository(session),
        folder_repository=FolderRepository(session),
        tag_repository=TagRepository(session),
        label_repository=LabelRepository(session),
    )


async def test_upload_stores_content_and_creates_version_with_metadata(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Q1.pdf", created_by=user_id
    )
    await db_session.commit()

    uploader = _FakeUploader()
    upload_service = _upload_service(db_session, uploader)

    version = await upload_service.upload_new_version(
        document.id,
        workspace_id=ws_id,
        filename="Q1.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4 fake content",
        created_by=user_id,
    )
    await db_session.commit()

    assert version.upload_status == UploadStatus.STORED.value
    assert version.is_current is True
    assert len(uploader.uploaded) == 1
    stored_key, stored_bytes = next(iter(uploader.uploaded.items()))
    assert stored_bytes == b"%PDF-1.4 fake content"

    metadata = await DocumentMetadataRepository(db_session).get_by_version(version.id)
    assert metadata is not None
    assert metadata.storage_path == stored_key
    assert metadata.file_size_bytes == len(b"%PDF-1.4 fake content")
    assert metadata.quarantine_status == QuarantineStatus.CLEAN.value


async def test_upload_rejects_oversized_file(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Big.pdf", created_by=user_id
    )
    await db_session.commit()

    upload_service = _upload_service(db_session, _FakeUploader(), max_size=10)

    with pytest.raises(ValidationException):
        await upload_service.upload_new_version(
            document.id,
            workspace_id=ws_id,
            filename="Big.pdf",
            content_type="application/pdf",
            content=b"x" * 100,
            created_by=user_id,
        )


async def test_upload_rejects_disallowed_mime_type(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Evil.exe", created_by=user_id
    )
    await db_session.commit()

    upload_service = _upload_service(
        db_session, _FakeUploader(), allowed_mime=["application/pdf"]
    )

    with pytest.raises(ValidationException):
        await upload_service.upload_new_version(
            document.id,
            workspace_id=ws_id,
            filename="Evil.exe",
            content_type="application/x-msdownload",
            content=b"MZ...",
            created_by=user_id,
        )


async def test_upload_rejects_empty_file(db_session: AsyncSession) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Empty.txt", created_by=user_id
    )
    await db_session.commit()

    upload_service = _upload_service(db_session, _FakeUploader())

    with pytest.raises(ValidationException):
        await upload_service.upload_new_version(
            document.id,
            workspace_id=ws_id,
            filename="Empty.txt",
            content_type="text/plain",
            content=b"",
            created_by=user_id,
        )


async def test_upload_rejects_a_checksum_mismatch_as_corrupted(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Report.txt", created_by=user_id
    )
    await db_session.commit()

    upload_service = _upload_service(db_session, _FakeUploader())

    with pytest.raises(ValidationException):
        await upload_service.upload_new_version(
            document.id,
            workspace_id=ws_id,
            filename="Report.txt",
            content_type="text/plain",
            content=b"hello world",
            created_by=user_id,
            expected_sha256="0" * 64,
        )


async def test_upload_rejects_duplicate_checksum_across_documents(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    doc_a = await documents.create(
        workspace_id=ws_id, folder_id=None, name="A.txt", created_by=user_id
    )
    doc_b = await documents.create(
        workspace_id=ws_id, folder_id=None, name="B.txt", created_by=user_id
    )
    await db_session.commit()

    upload_service = _upload_service(db_session, _FakeUploader())
    await upload_service.upload_new_version(
        doc_a.id,
        workspace_id=ws_id,
        filename="A.txt",
        content_type="text/plain",
        content=b"identical content",
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ConflictException):
        await upload_service.upload_new_version(
            doc_b.id,
            workspace_id=ws_id,
            filename="B.txt",
            content_type="text/plain",
            content=b"identical content",
            created_by=user_id,
        )


async def test_quarantined_upload_is_not_written_to_storage(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Bad.exe", created_by=user_id
    )
    await db_session.commit()

    uploader = _FakeUploader()
    upload_service = _upload_service(
        db_session, uploader, scanner=_AlwaysQuarantineScanner()
    )

    version = await upload_service.upload_new_version(
        document.id,
        workspace_id=ws_id,
        filename="Bad.exe",
        content_type="application/octet-stream",
        content=b"malicious-looking-bytes",
        created_by=user_id,
    )
    await db_session.commit()

    assert version.upload_status == UploadStatus.QUARANTINED.value
    assert version.is_current is False
    assert len(uploader.uploaded) == 0
    metadata = await DocumentMetadataRepository(db_session).get_by_version(version.id)
    assert metadata is not None
    assert metadata.quarantine_status == QuarantineStatus.QUARANTINED.value


async def test_successful_upload_records_a_document_uploaded_audit_event(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Q1.pdf", created_by=user_id
    )
    await db_session.commit()

    audit_repository = _FakeAuditRepository()
    upload_service = _upload_service(
        db_session, _FakeUploader(), audit_repository=audit_repository
    )

    await upload_service.upload_new_version(
        document.id,
        workspace_id=ws_id,
        filename="Q1.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4 fake content",
        created_by=user_id,
        ip_address="203.0.113.7",
    )

    assert len(audit_repository.events) == 1
    event = audit_repository.events[0]
    assert event.event_type == "document_uploaded"
    assert event.user_id == user_id
    assert event.workspace_id == ws_id
    assert event.ip_address == "203.0.113.7"


async def test_failed_validation_records_a_validation_failed_audit_event(
    db_session: AsyncSession,
) -> None:
    ws_id, user_id = await _seed(db_session)
    documents = _document_service(db_session)
    document = await documents.create(
        workspace_id=ws_id, folder_id=None, name="Empty.txt", created_by=user_id
    )
    await db_session.commit()

    audit_repository = _FakeAuditRepository()
    upload_service = _upload_service(
        db_session, _FakeUploader(), audit_repository=audit_repository
    )

    with pytest.raises(ValidationException):
        await upload_service.upload_new_version(
            document.id,
            workspace_id=ws_id,
            filename="Empty.txt",
            content_type="text/plain",
            content=b"",
            created_by=user_id,
        )

    assert len(audit_repository.events) == 1
    assert audit_repository.events[0].event_type == "document_upload_validation_failed"
