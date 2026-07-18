"""``UploadService``: CIS Phase 2 Prompt 2's Upload Pipeline —
validation, duplicate-checksum detection, virus scanning, MinIO storage,
and version/metadata creation, composed on top of
cerebrum.application.knowledge.version_service.VersionService rather
than duplicating its version-numbering/current-version logic.

Buffers the full upload into memory (bounded by
``DocumentSettings.max_file_size_bytes``, enforced while reading, not
only after) rather than a true zero-copy stream all the way to MinIO —
see cerebrum.infrastructure.storage.files.FileUploader's docstring for
why: computing the SHA256 checksum and rejecting an oversized upload
both require seeing the complete content before committing to a store.
"""

import hashlib
import uuid

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.config.documents import DocumentSettings
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.document_metadata import (
    QuarantineStatus,
)
from cerebrum.infrastructure.database.models.document_version import (
    DocumentVersion,
    UploadStatus,
    VersionType,
)
from cerebrum.infrastructure.security.virus_scan import VirusScanner
from cerebrum.infrastructure.storage.files import (
    FileUploader,
    FileValidationPolicy,
    validate_file,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.shared.errors.exceptions import ConflictException, ValidationException
from cerebrum.utils.clock import utcnow


class UploadService:
    def __init__(
        self,
        *,
        version_service: VersionService,
        document_repository: DocumentRepository,
        uploader: FileUploader,
        virus_scanner: VirusScanner,
        settings: DocumentSettings,
        audit_service: AuditService,
    ) -> None:
        self._versions = version_service
        self._documents = document_repository
        self._uploader = uploader
        self._scanner = virus_scanner
        self._settings = settings
        self._audit = audit_service

    async def upload_new_version(
        self,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
        created_by: uuid.UUID,
        version_type: VersionType = VersionType.MINOR,
        change_summary: str | None = None,
        expected_sha256: str | None = None,
        ip_address: str | None = None,
    ) -> DocumentVersion:
        try:
            validate_file(
                filename=filename,
                content_type=content_type,
                size_bytes=len(content),
                policy=FileValidationPolicy(
                    max_size_bytes=self._settings.max_file_size_bytes,
                    allowed_content_types=self._settings.allowed_mime_types_or_none,
                ),
            )

            checksum = hashlib.sha256(content).hexdigest()
            if expected_sha256 is not None and expected_sha256.lower() != checksum:
                # CIS Phase 2 Prompt 2's "Corrupted uploads" validation: the
                # client's own pre-computed checksum (if it supplied one)
                # disagreeing with what actually arrived means the transfer
                # was truncated or altered in transit.
                raise ValidationException(
                    "Uploaded content does not match the provided checksum — "
                    "the upload may be corrupted.",
                    context={"expected": expected_sha256, "actual": checksum},
                )

            duplicate = await self._documents.find_by_checksum(
                workspace_id=workspace_id, sha256_checksum=checksum
            )
            if duplicate is not None and duplicate.id != document_id:
                raise ConflictException(
                    f"A document with identical content already exists "
                    f"(document {duplicate.id}).",
                    context={"duplicate_document_id": str(duplicate.id)},
                )
        except (ValidationException, ConflictException) as exc:
            await self._audit.record(
                AuditEventType.DOCUMENT_UPLOAD_VALIDATION_FAILED,
                user_id=created_by,
                workspace_id=workspace_id,
                ip_address=ip_address,
                metadata={
                    "document_id": str(document_id),
                    "filename": filename,
                    "reason": str(exc),
                },
            )
            raise

        scan = await self._scanner.scan(content)

        object_key = f"{workspace_id}/{document_id}/{uuid.uuid4()}-{filename}"
        upload_status: UploadStatus
        if scan.status is QuarantineStatus.QUARANTINED:
            # A quarantined file is still recorded (for audit/visibility)
            # but never written to object storage — see this service's
            # docstring and cerebrum.infrastructure.security.virus_scan.
            upload_status = UploadStatus.QUARANTINED
        else:
            try:
                await self._uploader.upload(
                    object_key=object_key,
                    content=content,
                    content_type=content_type,
                    size_bytes=len(content),
                )
            except Exception as exc:
                await self._audit.record(
                    AuditEventType.DOCUMENT_STORAGE_FAILURE,
                    user_id=created_by,
                    workspace_id=workspace_id,
                    ip_address=ip_address,
                    metadata={
                        "document_id": str(document_id),
                        "object_key": object_key,
                        "reason": str(exc),
                    },
                )
                raise
            upload_status = UploadStatus.STORED

        version = await self._versions.create_version(
            document_id,
            workspace_id=workspace_id,
            version_type=version_type,
            change_summary=change_summary,
            mime_type=content_type,
            file_size_bytes=len(content),
            sha256_checksum=checksum,
            storage_path=object_key,
            original_filename=filename,
            uploaded_filename=object_key.rsplit("/", 1)[-1],
            uploaded_at=utcnow(),
            created_by=created_by,
            upload_status=upload_status,
            quarantine_status=scan.status,
            make_current=upload_status is not UploadStatus.QUARANTINED,
        )
        await self._audit.record(
            AuditEventType.DOCUMENT_UPLOADED,
            user_id=created_by,
            workspace_id=workspace_id,
            ip_address=ip_address,
            metadata={
                "document_id": str(document_id),
                "version_id": str(version.id),
                "upload_status": upload_status.value,
            },
        )
        return version

    async def delete_stored_object(self, storage_path: str) -> None:
        await self._uploader.delete(storage_path)
