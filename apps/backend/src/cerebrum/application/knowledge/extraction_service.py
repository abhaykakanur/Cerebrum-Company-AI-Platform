"""``ExtractionService``: CIS Phase 2 Prompt 3's Intelligent Document
Processing Pipeline — dispatches a
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`'s
stored content to the matching
cerebrum.infrastructure.extraction.registry format extractor, and
records the result as a
:class:`~cerebrum.infrastructure.database.models.document_extraction.DocumentExtraction`.

Runs synchronously within the request that triggers it (:meth:`extract`/
:meth:`retry`), not via a background worker — see
cerebrum.infrastructure.queue.redis_queue's docstring: no worker
implementation consumes cerebrum.workers.queue.Queue yet. This service
still creates/updates the same
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
rows CIS Phase 2 Prompt 2's
cerebrum.application.knowledge.processing_service.ProcessingService
manages, so that service's existing status/cancel/history methods
already work for extraction jobs without any new job-lifecycle code —
an extraction run just also happens to actually do the work,
synchronously, instead of leaving the job at ``PENDING`` forever.
:meth:`retry` duplicates ``ProcessingService.retry``'s validation
(failed/cancelled only, retry-budget check) rather than depending on
it, since retrying an extraction job must run the extraction inline
afterward — a plain re-enqueue (``ProcessingService.retry``'s job) would
leave the job ``PENDING`` with nothing to pick it up.
"""

import asyncio
import uuid
from typing import Any

from cerebrum.infrastructure.database.models.document_extraction import (
    DocumentExtraction,
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_metadata import (
    DocumentMetadata,
)
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.extraction.normalize import normalize_text
from cerebrum.infrastructure.extraction.registry import build_extractor_registry
from cerebrum.infrastructure.storage.files import FileDownloader
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
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

_IMAGE_MIME_PREFIX = "image/"


class ExtractionService:
    def __init__(
        self,
        *,
        extraction_repository: DocumentExtractionRepository,
        metadata_repository: DocumentMetadataRepository,
        version_repository: DocumentVersionRepository,
        document_repository: DocumentRepository,
        job_repository: ProcessingJobRepository,
        downloader: FileDownloader,
    ) -> None:
        self._extractions = extraction_repository
        self._metadata = metadata_repository
        self._versions = version_repository
        self._documents = document_repository
        self._jobs = job_repository
        self._downloader = downloader
        self._registry = build_extractor_registry()

    async def get_for_version(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> DocumentExtraction:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        extraction = await self._extractions.get_by_version(document_version_id)
        if extraction is None:
            raise NotFoundException(
                f"No extraction result for document version {document_version_id}."
            )
        return extraction

    async def extract(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> DocumentExtraction:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        metadata = await self._require_metadata(document_version_id)

        job = ProcessingJob(
            document_version_id=document_version_id,
            job_type=self._job_type_for(metadata).value,
            status=ProcessingJobStatus.RUNNING.value,
        )
        await self._jobs.add(job)
        return await self._run(job, metadata)

    async def retry(
        self, job_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> DocumentExtraction:
        job = await self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundException(f"No processing job with id {job_id}.")
        await self._require_version_in_workspace(
            job.document_version_id, workspace_id=workspace_id
        )
        if job.status not in (
            ProcessingJobStatus.FAILED.value,
            ProcessingJobStatus.CANCELLED.value,
        ):
            raise ValidationException(
                f"Only a failed or cancelled job can be retried (current status: "
                f"'{job.status}')."
            )
        if job.retry_count >= job.max_retries:
            raise ValidationException(
                f"Job {job_id} has exhausted its retry budget "
                f"({job.retry_count}/{job.max_retries})."
            )
        metadata = await self._require_metadata(job.document_version_id)

        job.retry_count += 1
        job.status = ProcessingJobStatus.RUNNING.value
        job.error_message = None
        job.progress_percent = 0
        await self._jobs.update(job)
        return await self._run(job, metadata)

    async def _run(
        self, job: ProcessingJob, metadata: DocumentMetadata
    ) -> DocumentExtraction:
        extractor = self._registry.get(metadata.mime_type)
        if extractor is None:
            return await self._fail(
                job,
                status=ExtractionStatus.UNSUPPORTED_FORMAT,
                error_message=f"Unsupported format: '{metadata.mime_type}'.",
            )

        job.progress_percent = 25
        await self._jobs.update(job)

        try:
            content = b"".join(
                [
                    chunk
                    async for chunk in self._downloader.download(
                        object_key=metadata.storage_path
                    )
                ]
            )
            job.progress_percent = 60
            await self._jobs.update(job)
            result = await asyncio.to_thread(extractor.extract, content)
            normalized_text = normalize_text(result.text)
        except (
            Exception
        ) as exc:  # noqa: BLE001 - any parser/download failure is a job failure, not a crash
            return await self._fail(
                job, status=ExtractionStatus.FAILED, error_message=str(exc)
            )

        job.status = ProcessingJobStatus.COMPLETED.value
        job.progress_percent = 100
        await self._jobs.update(job)
        return await self._persist(
            job,
            status=ExtractionStatus.COMPLETED,
            text=normalized_text,
            extracted_metadata=result.metadata,
            error_message=None,
        )

    async def _fail(
        self, job: ProcessingJob, *, status: ExtractionStatus, error_message: str
    ) -> DocumentExtraction:
        job.status = ProcessingJobStatus.FAILED.value
        job.error_message = error_message
        job.progress_percent = 0
        await self._jobs.update(job)
        return await self._persist(
            job,
            status=status,
            text=None,
            extracted_metadata={},
            error_message=error_message,
        )

    async def _persist(
        self,
        job: ProcessingJob,
        *,
        status: ExtractionStatus,
        text: str | None,
        extracted_metadata: dict[str, Any],
        error_message: str | None,
    ) -> DocumentExtraction:
        existing = await self._extractions.get_by_version(job.document_version_id)
        if existing is not None:
            existing.processing_job_id = job.id
            existing.status = status.value
            existing.extracted_text = text
            existing.extracted_metadata = extracted_metadata
            existing.error_message = error_message
            return await self._extractions.update(existing)
        return await self._extractions.add(
            DocumentExtraction(
                document_version_id=job.document_version_id,
                processing_job_id=job.id,
                status=status.value,
                extracted_text=text,
                extracted_metadata=extracted_metadata,
                error_message=error_message,
            )
        )

    async def _require_metadata(
        self, document_version_id: uuid.UUID
    ) -> DocumentMetadata:
        metadata = await self._metadata.get_by_version(document_version_id)
        if metadata is None:
            raise ValidationException(
                f"Document version {document_version_id} has no stored content to "
                f"extract."
            )
        return metadata

    async def _require_version_in_workspace(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> None:
        version = await self._versions.get_by_id(document_version_id)
        if version is None:
            raise NotFoundException(
                f"No document version with id {document_version_id}."
            )
        document = await self._documents.get_by_id(version.document_id)
        if document is None or document.workspace_id != workspace_id:
            raise NotFoundException(
                f"No document version with id {document_version_id}."
            )

    @staticmethod
    def _job_type_for(metadata: DocumentMetadata) -> ProcessingJobType:
        if metadata.mime_type.startswith(_IMAGE_MIME_PREFIX):
            return ProcessingJobType.OCR
        return ProcessingJobType.PARSING
