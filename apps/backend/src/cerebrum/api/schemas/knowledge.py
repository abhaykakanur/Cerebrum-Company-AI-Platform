"""Request/response schemas for the Knowledge Domain API — CIS Phase 2
Prompt 1. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` (``from_attributes=True``)
so a route can return ``XResponse.model_validate(orm_object)`` directly.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel
from cerebrum.infrastructure.database.models.chunk import ChunkingStrategy
from cerebrum.infrastructure.database.models.document import DocumentStatus
from cerebrum.infrastructure.database.models.document_extraction import (
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_manifest import ManifestStatus
from cerebrum.infrastructure.database.models.document_metadata import (
    QuarantineStatus,
)
from cerebrum.infrastructure.database.models.document_version import (
    UploadStatus,
    VersionType,
)
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJobStatus,
    ProcessingJobType,
)

# --- Organization -------------------------------------------------------------


class OrganizationResponse(APIModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class OrganizationUpdateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)


# --- Workspace ------------------------------------------------------------


class WorkspaceResponse(APIModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class WorkspaceCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)


class WorkspaceUpdateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)


# --- Folder -----------------------------------------------------------------


class FolderResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    version: int
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FolderCreateRequest(APIModel):
    parent_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)


class FolderRenameRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)


class FolderMoveRequest(APIModel):
    new_parent_id: uuid.UUID | None = None


# --- Document -----------------------------------------------------------------


class DocumentResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    folder_id: uuid.UUID | None
    name: str
    status: DocumentStatus
    current_version_id: uuid.UUID | None
    version: int
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentCreateRequest(APIModel):
    folder_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)


class DocumentRenameRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)


class DocumentMoveRequest(APIModel):
    new_folder_id: uuid.UUID | None = None


class DocumentStatusUpdateRequest(APIModel):
    status: DocumentStatus


# --- Document Version -----------------------------------------------------


class DocumentVersionResponse(APIModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    version_type: VersionType
    is_current: bool
    upload_status: UploadStatus
    change_summary: str | None
    created_at: datetime
    created_by: uuid.UUID | None


class DocumentVersionCreateRequest(APIModel):
    """CIS Phase 2 Prompt 1's metadata-only version creation — no binary
    upload here, see cerebrum.application.knowledge.version_service's
    docstring; CIS Phase 2 Prompt 2 adds the real upload endpoint.
    """

    version_type: VersionType = VersionType.MINOR
    change_summary: str | None = Field(default=None, max_length=2000)
    mime_type: str = Field(max_length=255)
    file_size_bytes: int = Field(gt=0)
    sha256_checksum: str = Field(min_length=64, max_length=64)
    storage_path: str = Field(max_length=1024)
    original_filename: str = Field(max_length=500)
    uploaded_filename: str = Field(max_length=500)
    uploaded_at: datetime
    make_current: bool = True


# --- Document Metadata ------------------------------------------------------


class DocumentMetadataResponse(APIModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    mime_type: str
    file_size_bytes: int
    sha256_checksum: str
    storage_path: str
    original_filename: str
    uploaded_filename: str
    uploaded_at: datetime
    quarantine_status: QuarantineStatus


# --- Tag ----------------------------------------------------------------------


class TagResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    created_at: datetime


class TagCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)


class TagUpdateRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)


# --- Label --------------------------------------------------------------------


class LabelResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    color: str | None
    created_at: datetime


class LabelCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, min_length=7, max_length=7)


class LabelUpdateRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, min_length=7, max_length=7)


# --- Collection -----------------------------------------------------------


class CollectionResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class CollectionCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CollectionUpdateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class BulkDocumentIdsRequest(APIModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)


class BulkOperationResponse(APIModel):
    requested: int
    succeeded: int


# --- Upload / Download (Phase 2, Prompt 2) --------------------------------


class DownloadUrlResponse(APIModel):
    url: str
    expires_in_seconds: int


# --- Processing Jobs (Phase 2, Prompt 2) ------------------------------------


class ProcessingJobResponse(APIModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    job_type: ProcessingJobType
    status: ProcessingJobStatus
    progress_percent: int
    retry_count: int
    max_retries: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class EnqueueProcessingJobRequest(APIModel):
    job_type: ProcessingJobType


# --- Extraction (Phase 2, Prompt 3) ------------------------------------------


class DocumentExtractionResponse(APIModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    processing_job_id: uuid.UUID | None
    status: ExtractionStatus
    extracted_text: str | None
    extracted_metadata: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


# --- Chunking & Knowledge Preparation (Phase 2, Prompt 4) --------------------


class ChunkResponse(APIModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    extraction_id: uuid.UUID
    parent_chunk_id: uuid.UUID | None
    strategy: ChunkingStrategy
    chunk_index: int
    text: str
    character_count: int
    start_offset: int
    end_offset: int
    overlap_with_previous: int
    chunk_metadata: dict[str, Any]
    created_at: datetime


class DocumentManifestResponse(APIModel):
    id: uuid.UUID
    document_version_id: uuid.UUID
    extraction_id: uuid.UUID | None
    status: ManifestStatus
    chunking_strategy: str | None
    chunk_count: int
    total_character_count: int
    statistics: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PipelineProgressResponse(APIModel):
    extraction_status: str | None
    extraction_progress_percent: int
    chunking_status: str | None
    chunking_progress_percent: int
    overall_progress_percent: int


class ReprocessRequest(APIModel):
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    force: bool = False


class CancelProcessingResponse(APIModel):
    cancelled_job_count: int
