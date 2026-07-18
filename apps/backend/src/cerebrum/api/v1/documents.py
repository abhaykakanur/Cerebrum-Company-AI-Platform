"""The Document API surface — CIS Phase 2 Prompt 1's central business
entity, plus its nested Versions and Tag/Label assignment. See
cerebrum.api.v1.folders's docstring for the workspace-scoping/RBAC
pattern every route here reuses identically.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge import (
    BulkDocumentIdsRequest,
    BulkOperationResponse,
    CancelProcessingResponse,
    ChunkResponse,
    DocumentCreateRequest,
    DocumentExtractionResponse,
    DocumentManifestResponse,
    DocumentMetadataResponse,
    DocumentMoveRequest,
    DocumentRenameRequest,
    DocumentResponse,
    DocumentStatusUpdateRequest,
    DocumentVersionCreateRequest,
    DocumentVersionResponse,
    DownloadUrlResponse,
    EnqueueProcessingJobRequest,
    PipelineProgressResponse,
    ProcessingJobResponse,
    ReprocessRequest,
)
from cerebrum.dependencies.auth import (
    AuditServiceDep,
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.knowledge import (
    ChunkingServiceDep,
    DocumentServiceDep,
    ExtractionServiceDep,
    FileDownloaderDep,
    KnowledgePreparationServiceDep,
    MetadataServiceDep,
    ProcessingServiceDep,
    UploadServiceDep,
    VersionServiceDep,
)
from cerebrum.dependencies.pagination import FilterDep, PaginationDep, SortDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.document_version import VersionType
from cerebrum.middleware.context import get_client_ip
from cerebrum.repositories.contracts import map_page
from cerebrum.shared.errors.exceptions import NotFoundException

router = APIRouter(
    prefix="/documents", tags=["Documents"], responses=STANDARD_ERROR_RESPONSES
)


@router.get(
    "",
    response_model=SuccessResponse[list[DocumentResponse]],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def list_documents(
    workspace_id: WorkspaceIdDep,
    documents: DocumentServiceDep,
    pagination: PaginationDep,
    sort: SortDep,
    filters: FilterDep,
    settings: SettingsDep,
) -> SuccessResponse[list[DocumentResponse]]:
    """Supports filtering/sorting/search by metadata via the standard
    ``?filter=field:operator:value`` query syntax — see
    docs/architecture/api/dependency-guide.md — e.g.
    ``?filter=name:contains:report``.
    """
    page = await documents.list_in_workspace(
        workspace_id=workspace_id, pagination=pagination, filters=filters, sort=sort
    )
    return build_collection_response(
        map_page(page, DocumentResponse.model_validate), settings=settings
    )


@router.post(
    "",
    response_model=SuccessResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def create_document(
    body: DocumentCreateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentResponse]:
    document = await documents.create(
        workspace_id=workspace_id,
        folder_id=body.folder_id,
        name=body.name,
        created_by=current_user.id,
    )
    return build_success_response(
        DocumentResponse.model_validate(document), settings=settings
    )


# Registered before "/{document_id}" below: see cerebrum.api.v1.collections's
# route-ordering comment — a literal segment sharing a path level with a
# "{document_id}" parameter must be registered first, or FastAPI/Starlette
# would try to parse the literal as a UUID and 422.
@router.post(
    "/bulk-delete",
    response_model=SuccessResponse[BulkOperationResponse],
    dependencies=[Depends(require_permission("documents:delete"))],
)
async def bulk_delete_documents(
    request: Request,
    body: BulkDocumentIdsRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    audit: AuditServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[BulkOperationResponse]:
    """CIS Phase 2 Prompt 2's Bulk Delete. Partial success, matching
    cerebrum.application.knowledge.collection_service.CollectionService.add_documents_bulk's
    precedent: an ID that doesn't resolve in this workspace is skipped,
    not a hard failure of the whole batch.
    """
    succeeded = 0
    for document_id in body.document_ids:
        try:
            await documents.soft_delete(document_id, workspace_id=workspace_id)
            succeeded += 1
            await audit.record(
                AuditEventType.DOCUMENT_DELETED,
                user_id=current_user.id,
                workspace_id=workspace_id,
                ip_address=get_client_ip(request),
                metadata={"document_id": str(document_id)},
            )
        except NotFoundException:
            continue
    return build_success_response(
        BulkOperationResponse(requested=len(body.document_ids), succeeded=succeeded),
        settings=settings,
    )


@router.post(
    "/upload-batch",
    response_model=SuccessResponse[list[DocumentVersionResponse]],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def upload_documents_batch(
    request: Request,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    upload_service: UploadServiceDep,
    settings: SettingsDep,
    files: Annotated[list[UploadFile], File()],
    folder_id: Annotated[uuid.UUID | None, Form()] = None,
) -> SuccessResponse[list[DocumentVersionResponse]]:
    """CIS Phase 2 Prompt 2's Multiple Upload: one new Document (named
    after the uploaded file) plus its first Version, per file. Stops at
    the first failure (a duplicate name/checksum, a validation failure)
    rather than silently skipping it — unlike bulk delete/collection
    membership, a partially-failed batch upload leaving the caller
    unsure which files actually made it in is a worse experience than a
    single clear error naming which file failed and why.
    """
    versions = []
    for upload in files:
        filename = upload.filename or "upload"
        document = await documents.create(
            workspace_id=workspace_id,
            folder_id=folder_id,
            name=filename,
            created_by=current_user.id,
        )
        content = await upload.read()
        version = await upload_service.upload_new_version(
            document.id,
            workspace_id=workspace_id,
            filename=filename,
            content_type=upload.content_type or "application/octet-stream",
            content=content,
            created_by=current_user.id,
            ip_address=get_client_ip(request),
        )
        versions.append(version)
    responses = [DocumentVersionResponse.model_validate(v) for v in versions]
    return build_success_response(responses, settings=settings)


@router.get(
    "/{document_id}",
    response_model=SuccessResponse[DocumentResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_document(
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    documents: DocumentServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentResponse]:
    document = await documents.get(document_id, workspace_id=workspace_id)
    return build_success_response(
        DocumentResponse.model_validate(document), settings=settings
    )


@router.patch(
    "/{document_id}",
    response_model=SuccessResponse[DocumentResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def rename_document(
    document_id: uuid.UUID,
    body: DocumentRenameRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentResponse]:
    document = await documents.rename(
        document_id,
        workspace_id=workspace_id,
        name=body.name,
        updated_by=current_user.id,
    )
    return build_success_response(
        DocumentResponse.model_validate(document), settings=settings
    )


@router.post(
    "/{document_id}/move",
    response_model=SuccessResponse[DocumentResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def move_document(
    document_id: uuid.UUID,
    body: DocumentMoveRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentResponse]:
    document = await documents.move(
        document_id,
        workspace_id=workspace_id,
        new_folder_id=body.new_folder_id,
        updated_by=current_user.id,
    )
    return build_success_response(
        DocumentResponse.model_validate(document), settings=settings
    )


@router.post(
    "/{document_id}/status",
    response_model=SuccessResponse[DocumentResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def change_document_status(
    document_id: uuid.UUID,
    body: DocumentStatusUpdateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentResponse]:
    document = await documents.change_status(
        document_id,
        workspace_id=workspace_id,
        status=body.status,
        updated_by=current_user.id,
    )
    return build_success_response(
        DocumentResponse.model_validate(document), settings=settings
    )


@router.post(
    "/{document_id}/upload",
    response_model=SuccessResponse[DocumentVersionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def upload_document_version(
    request: Request,
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    upload_service: UploadServiceDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    version_type: Annotated[VersionType, Form()] = VersionType.MINOR,
    change_summary: Annotated[str | None, Form()] = None,
    expected_sha256: Annotated[str | None, Form()] = None,
) -> SuccessResponse[DocumentVersionResponse]:
    """CIS Phase 2 Prompt 2's Single Upload: a new
    :class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
    for an existing document — see
    cerebrum.application.knowledge.upload_service.UploadService for
    validation (MIME type, size, duplicate checksum, corrupted-upload
    detection), quarantine handling, and MinIO storage.
    """
    content = await file.read()
    version = await upload_service.upload_new_version(
        document_id,
        workspace_id=workspace_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        created_by=current_user.id,
        version_type=version_type,
        change_summary=change_summary,
        expected_sha256=expected_sha256,
        ip_address=get_client_ip(request),
    )
    return build_success_response(
        DocumentVersionResponse.model_validate(version), settings=settings
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("documents:delete"))],
)
async def delete_document(
    request: Request,
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    audit: AuditServiceDep,
) -> None:
    await documents.soft_delete(document_id, workspace_id=workspace_id)
    await audit.record(
        AuditEventType.DOCUMENT_DELETED,
        user_id=current_user.id,
        workspace_id=workspace_id,
        ip_address=get_client_ip(request),
        metadata={"document_id": str(document_id)},
    )


@router.post(
    "/{document_id}/restore",
    response_model=SuccessResponse[DocumentResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def restore_document(
    request: Request,
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    audit: AuditServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentResponse]:
    document = await documents.restore(document_id, workspace_id=workspace_id)
    await audit.record(
        AuditEventType.DOCUMENT_RESTORED,
        user_id=current_user.id,
        workspace_id=workspace_id,
        ip_address=get_client_ip(request),
        metadata={"document_id": str(document_id)},
    )
    return build_success_response(
        DocumentResponse.model_validate(document), settings=settings
    )


@router.post(
    "/{document_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def assign_tag(
    document_id: uuid.UUID,
    tag_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    documents: DocumentServiceDep,
) -> None:
    await documents.assign_tag(document_id, tag_id, workspace_id=workspace_id)


@router.delete(
    "/{document_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def remove_tag(
    document_id: uuid.UUID,
    tag_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    documents: DocumentServiceDep,
) -> None:
    await documents.remove_tag(document_id, tag_id, workspace_id=workspace_id)


@router.post(
    "/{document_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def assign_label(
    document_id: uuid.UUID,
    label_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    documents: DocumentServiceDep,
) -> None:
    await documents.assign_label(document_id, label_id, workspace_id=workspace_id)


@router.delete(
    "/{document_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def remove_label(
    document_id: uuid.UUID,
    label_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    documents: DocumentServiceDep,
) -> None:
    await documents.remove_label(document_id, label_id, workspace_id=workspace_id)


# --- Versions (nested) -------------------------------------------------------


@router.get(
    "/{document_id}/versions",
    response_model=SuccessResponse[list[DocumentVersionResponse]],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def list_versions(
    document_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    versions: VersionServiceDep,
    pagination: PaginationDep,
    settings: SettingsDep,
) -> SuccessResponse[list[DocumentVersionResponse]]:
    page = await versions.list_by_document(
        document_id, workspace_id=workspace_id, pagination=pagination
    )
    return build_collection_response(
        map_page(page, DocumentVersionResponse.model_validate), settings=settings
    )


@router.post(
    "/{document_id}/versions",
    response_model=SuccessResponse[DocumentVersionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def create_version(
    document_id: uuid.UUID,
    body: DocumentVersionCreateRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    versions: VersionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentVersionResponse]:
    version = await versions.create_version(
        document_id,
        workspace_id=workspace_id,
        version_type=body.version_type,
        change_summary=body.change_summary,
        mime_type=body.mime_type,
        file_size_bytes=body.file_size_bytes,
        sha256_checksum=body.sha256_checksum,
        storage_path=body.storage_path,
        original_filename=body.original_filename,
        uploaded_filename=body.uploaded_filename,
        uploaded_at=body.uploaded_at,
        created_by=current_user.id,
        make_current=body.make_current,
    )
    return build_success_response(
        DocumentVersionResponse.model_validate(version), settings=settings
    )


@router.get(
    "/{document_id}/versions/{version_id}",
    response_model=SuccessResponse[DocumentVersionResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    versions: VersionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentVersionResponse]:
    version = await versions.get(version_id)
    return build_success_response(
        DocumentVersionResponse.model_validate(version), settings=settings
    )


@router.get(
    "/{document_id}/versions/{version_id}/metadata",
    response_model=SuccessResponse[DocumentMetadataResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_version_metadata(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    metadata_service: MetadataServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentMetadataResponse]:
    metadata = await metadata_service.get_for_version(version_id)
    return build_success_response(
        DocumentMetadataResponse.model_validate(metadata), settings=settings
    )


@router.post(
    "/{document_id}/versions/{version_id}/restore",
    response_model=SuccessResponse[DocumentVersionResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def restore_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    versions: VersionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentVersionResponse]:
    version = await versions.set_current(
        document_id, version_id, workspace_id=workspace_id
    )
    return build_success_response(
        DocumentVersionResponse.model_validate(version), settings=settings
    )


@router.get(
    "/{document_id}/versions/{version_id}/download",
    dependencies=[Depends(require_permission("documents:read"))],
)
async def download_version(
    request: Request,
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    metadata_service: MetadataServiceDep,
    downloader: FileDownloaderDep,
    audit: AuditServiceDep,
) -> StreamingResponse:
    """CIS Phase 2 Prompt 2's Download endpoint — streams the version's
    binary content straight from MinIO through to the HTTP response; see
    cerebrum.infrastructure.storage.minio_files.MinIOFileDownloader's
    docstring for the "buffered-in-a-worker-thread, then streamed to the
    client" tradeoff.
    """
    metadata = await metadata_service.get_for_version(version_id)
    content_disposition = f'attachment; filename="{metadata.original_filename}"'
    await audit.record(
        AuditEventType.DOCUMENT_DOWNLOADED,
        user_id=current_user.id,
        workspace_id=workspace_id,
        ip_address=get_client_ip(request),
        metadata={"document_id": str(document_id), "version_id": str(version_id)},
    )
    return StreamingResponse(
        downloader.download(object_key=metadata.storage_path),
        media_type=metadata.mime_type,
        headers={"Content-Disposition": content_disposition},
    )


@router.get(
    "/{document_id}/versions/{version_id}/download-url",
    response_model=SuccessResponse[DownloadUrlResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_download_url(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    metadata_service: MetadataServiceDep,
    downloader: FileDownloaderDep,
    settings: SettingsDep,
) -> SuccessResponse[DownloadUrlResponse]:
    """CIS Phase 2 Prompt 2's Signed URLs — a time-limited, direct-to-MinIO
    download link, for a client that would rather fetch the object
    itself than proxy the bytes through this API.
    """
    metadata = await metadata_service.get_for_version(version_id)
    expires_in_seconds = 3600
    url = await downloader.presigned_download_url(
        metadata.storage_path, expires_in_seconds=expires_in_seconds
    )
    return build_success_response(
        DownloadUrlResponse(url=url, expires_in_seconds=expires_in_seconds),
        settings=settings,
    )


# --- Processing Jobs (nested, CIS Phase 2 Prompt 2) --------------------------


@router.get(
    "/{document_id}/versions/{version_id}/processing-jobs",
    response_model=SuccessResponse[list[ProcessingJobResponse]],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def list_processing_jobs(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    processing: ProcessingServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[list[ProcessingJobResponse]]:
    """CIS Phase 2 Prompt 2's Processing History for one document
    version — every job ever enqueued against it, in insertion order.
    """
    jobs = await processing.list_for_version(version_id, workspace_id=workspace_id)
    responses = [ProcessingJobResponse.model_validate(j) for j in jobs]
    return build_success_response(responses, settings=settings)


@router.post(
    "/{document_id}/versions/{version_id}/processing-jobs",
    response_model=SuccessResponse[ProcessingJobResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def enqueue_processing_job(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    body: EnqueueProcessingJobRequest,
    workspace_id: WorkspaceIdDep,
    processing: ProcessingServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[ProcessingJobResponse]:
    job = await processing.enqueue(
        version_id, workspace_id=workspace_id, job_type=body.job_type
    )
    return build_success_response(
        ProcessingJobResponse.model_validate(job), settings=settings
    )


# --- Extraction (nested, CIS Phase 2 Prompt 3) --------------------------------


@router.post(
    "/{document_id}/versions/{version_id}/extract",
    response_model=SuccessResponse[DocumentExtractionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def extract_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    extraction: ExtractionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentExtractionResponse]:
    """CIS Phase 2 Prompt 3's Intelligent Document Processing Pipeline:
    parses the version's stored content (dispatched by MIME type — see
    cerebrum.infrastructure.extraction.registry) and stores the
    resulting text/metadata. Runs synchronously, creating and completing
    a :class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
    in the same call — see
    cerebrum.application.knowledge.extraction_service.ExtractionService's
    docstring for why (no background worker consumes a queue yet).
    """
    result = await extraction.extract(version_id, workspace_id=workspace_id)
    return build_success_response(
        DocumentExtractionResponse.model_validate(result), settings=settings
    )


@router.get(
    "/{document_id}/versions/{version_id}/extraction",
    response_model=SuccessResponse[DocumentExtractionResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_extraction(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    extraction: ExtractionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentExtractionResponse]:
    result = await extraction.get_for_version(version_id, workspace_id=workspace_id)
    return build_success_response(
        DocumentExtractionResponse.model_validate(result), settings=settings
    )


@router.post(
    "/{document_id}/versions/{version_id}/extraction/retry/{job_id}",
    response_model=SuccessResponse[DocumentExtractionResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def retry_extraction(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    job_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    extraction: ExtractionServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentExtractionResponse]:
    """Re-runs extraction for a failed or cancelled job — unlike
    cerebrum.api.v1.processing_jobs's generic retry (which only resets a
    job's status/queue membership), this actually re-executes the
    extraction, since no worker will otherwise pick the job back up.
    """
    result = await extraction.retry(job_id, workspace_id=workspace_id)
    return build_success_response(
        DocumentExtractionResponse.model_validate(result), settings=settings
    )


# --- Chunking & Knowledge Preparation (nested, CIS Phase 2 Prompt 4) ---------


@router.post(
    "/{document_id}/versions/{version_id}/reprocess",
    response_model=SuccessResponse[DocumentManifestResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("documents:write"))],
)
async def reprocess_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    body: ReprocessRequest,
    workspace_id: WorkspaceIdDep,
    knowledge_preparation: KnowledgePreparationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentManifestResponse]:
    """CIS Phase 2 Prompt 4's Processing Orchestration entry point: runs
    Extraction (Prompt 3) then Chunking end to end and returns the
    resulting
    :class:`~cerebrum.infrastructure.database.models.document_manifest.DocumentManifest`.
    ``force=false`` (the default) skips a stage that already succeeded —
    the same call resumes a pipeline that previously failed partway
    through, or fully re-runs it with ``force=true`` — see
    cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService's
    docstring.
    """
    manifest = await knowledge_preparation.prepare(
        version_id, workspace_id=workspace_id, strategy=body.strategy, force=body.force
    )
    return build_success_response(
        DocumentManifestResponse.model_validate(manifest), settings=settings
    )


@router.get(
    "/{document_id}/versions/{version_id}/manifest",
    response_model=SuccessResponse[DocumentManifestResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_manifest(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    knowledge_preparation: KnowledgePreparationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[DocumentManifestResponse]:
    manifest = await knowledge_preparation.get_manifest(
        version_id, workspace_id=workspace_id
    )
    return build_success_response(
        DocumentManifestResponse.model_validate(manifest), settings=settings
    )


@router.get(
    "/{document_id}/versions/{version_id}/chunks",
    response_model=SuccessResponse[list[ChunkResponse]],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def list_chunks(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    chunking: ChunkingServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[list[ChunkResponse]]:
    chunks = await chunking.list_chunks(version_id, workspace_id=workspace_id)
    responses = [ChunkResponse.model_validate(c) for c in chunks]
    return build_success_response(responses, settings=settings)


@router.get(
    "/{document_id}/versions/{version_id}/progress",
    response_model=SuccessResponse[PipelineProgressResponse],
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_pipeline_progress(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    knowledge_preparation: KnowledgePreparationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[PipelineProgressResponse]:
    progress = await knowledge_preparation.get_progress(
        version_id, workspace_id=workspace_id
    )
    return build_success_response(
        PipelineProgressResponse.model_validate(progress), settings=settings
    )


@router.post(
    "/{document_id}/versions/{version_id}/cancel-processing",
    response_model=SuccessResponse[CancelProcessingResponse],
    dependencies=[Depends(require_permission("documents:write"))],
)
async def cancel_processing(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    knowledge_preparation: KnowledgePreparationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CancelProcessingResponse]:
    """Cancels every still-pending/running processing job for this
    version — see
    cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService.cancel's
    docstring for when that is (and is not) a no-op.
    """
    cancelled_count = await knowledge_preparation.cancel(
        version_id, workspace_id=workspace_id
    )
    return build_success_response(
        CancelProcessingResponse(cancelled_job_count=cancelled_count),
        settings=settings,
    )
