"""``VersionService``: creates and manages
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
rows — CIS Phase 2 Prompt 1's Versioning requirement (Major/Minor,
Current/Previous, Change Summary, Restore Version). Version Consistency
validation lives here: version numbers are a strictly incrementing
per-document sequence (see
cerebrum.repositories.postgres.document_version_repository.DocumentVersionRepository.get_next_version_number),
and exactly one version is ever ``is_current`` at a time.

CIS Phase 2 Prompt 1 explicitly excludes Binary Uploads — ``create``
below takes already-known metadata fields (mime type, size, checksum,
storage path, filenames) directly, as a caller-supplied "register this
version's metadata" operation; CIS Phase 2 Prompt 2 is what adds the
actual file-upload endpoint that computes these fields from real bytes
and calls the same service underneath.
"""

import uuid
from datetime import datetime

from cerebrum.infrastructure.database.models.document import DocumentStatus
from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
    QuarantineStatus,
)
from cerebrum.infrastructure.database.models.document_version import (
    DocumentVersion,
    UploadStatus,
    VersionType,
)
from cerebrum.repositories.contracts import Page, Pagination
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException


class VersionService:
    def __init__(
        self,
        *,
        version_repository: DocumentVersionRepository,
        metadata_repository: DocumentMetadataRepository,
        document_repository: DocumentRepository,
    ) -> None:
        self._versions = version_repository
        self._metadata = metadata_repository
        self._documents = document_repository

    async def create_version(
        self,
        document_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        version_type: VersionType,
        change_summary: str | None,
        mime_type: str,
        file_size_bytes: int,
        sha256_checksum: str,
        storage_path: str,
        original_filename: str,
        uploaded_filename: str,
        uploaded_at: datetime,
        created_by: uuid.UUID,
        upload_status: UploadStatus = UploadStatus.UPLOADED,
        quarantine_status: QuarantineStatus = QuarantineStatus.PENDING,
        make_current: bool = True,
    ) -> DocumentVersion:
        document = await self._documents.get_by_id(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(f"No document with id {document_id}.")

        version_number = await self._versions.get_next_version_number(document_id)
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            version_type=version_type.value,
            change_summary=change_summary,
            created_by=created_by,
            upload_status=upload_status.value,
        )
        await self._versions.add(version)

        metadata = DocumentMetadata(
            document_version_id=version.id,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            sha256_checksum=sha256_checksum,
            storage_path=storage_path,
            original_filename=original_filename,
            uploaded_filename=uploaded_filename,
            uploaded_at=uploaded_at,
            quarantine_status=quarantine_status.value,
        )
        await self._metadata.add(metadata)

        if make_current:
            await self.set_current(document_id, version.id, workspace_id=workspace_id)
        if document.status == DocumentStatus.DRAFT.value:
            document.status = DocumentStatus.UPLOADED.value
            document.updated_by = created_by
            await self._documents.update(document)

        return version

    async def get(self, version_id: uuid.UUID) -> DocumentVersion:
        version = await self._versions.get_by_id(version_id)
        if version is None:
            raise NotFoundException(f"No document version with id {version_id}.")
        return version

    async def list_by_document(
        self, document_id: uuid.UUID, *, workspace_id: uuid.UUID, pagination: Pagination
    ) -> Page[DocumentVersion]:
        document = await self._documents.get_by_id(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(f"No document with id {document_id}.")
        return await self._versions.list_by_document(document_id, pagination=pagination)

    async def set_current(
        self,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
    ) -> DocumentVersion:
        """CIS Phase 2 Prompt 1's Restore Version: makes an existing
        (possibly older) version current again. Version Consistency:
        rejects a ``version_id`` that does not actually belong to
        ``document_id`` — restoring version 3 of a *different* document
        onto this one would silently corrupt both documents' history.
        """
        document = await self._documents.get_by_id(document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(f"No document with id {document_id}.")
        version = await self.get(version_id)
        if version.document_id != document_id:
            raise ValidationException(
                f"Version {version_id} does not belong to document {document_id}."
            )

        await self._versions.unset_current(document_id)
        version.is_current = True
        await self._versions.update(version)

        document.current_version_id = version.id
        await self._documents.update(document)
        return version
