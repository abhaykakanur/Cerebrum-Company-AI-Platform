"""``ProcessingService``: CIS Phase 2 Prompt 2's Background Processing
framework — creates, enqueues, retries, and cancels
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
rows. No job type's actual work (OCR, parsing, chunking, embeddings) is
performed here — see cerebrum.infrastructure.queue.redis_queue's
docstring; this service only manages job *records* and their queue
membership.

Every method takes ``workspace_id`` and validates it against the job's
owning document (via its document version) before returning/mutating
anything — a ``ProcessingJob`` has no ``workspace_id`` column of its own
(it belongs to a ``DocumentVersion``, which belongs to a ``Document``),
so without this check a job ID alone would leak cross-tenant processing
status. Same tenant-isolation discipline as every other Knowledge Domain
service — see cerebrum.application.knowledge.workspace_service's
docstring.
"""

import uuid

from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException
from cerebrum.workers.base import Job
from cerebrum.workers.queue import Queue


class ProcessingService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        version_repository: DocumentVersionRepository,
        document_repository: DocumentRepository,
        queue: Queue[uuid.UUID],
    ) -> None:
        self._jobs = job_repository
        self._versions = version_repository
        self._documents = document_repository
        self._queue = queue

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

    async def _get_owned(
        self, job_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> ProcessingJob:
        job = await self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundException(f"No processing job with id {job_id}.")
        await self._require_version_in_workspace(
            job.document_version_id, workspace_id=workspace_id
        )
        return job

    async def enqueue(
        self,
        document_version_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        job_type: ProcessingJobType,
    ) -> ProcessingJob:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        job = ProcessingJob(
            document_version_id=document_version_id,
            job_type=job_type.value,
            status=ProcessingJobStatus.PENDING.value,
        )
        await self._jobs.add(job)
        await self._queue.enqueue(Job(payload=job.id))
        return job

    async def get(self, job_id: uuid.UUID, *, workspace_id: uuid.UUID) -> ProcessingJob:
        return await self._get_owned(job_id, workspace_id=workspace_id)

    async def list_for_version(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[ProcessingJob]:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        return await self._jobs.list_by_document_version(document_version_id)

    async def retry(
        self, job_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> ProcessingJob:
        job = await self._get_owned(job_id, workspace_id=workspace_id)
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
        job.retry_count += 1
        job.status = ProcessingJobStatus.PENDING.value
        job.error_message = None
        job.progress_percent = 0
        await self._jobs.update(job)
        await self._queue.enqueue(Job(payload=job.id))
        return job

    async def cancel(
        self, job_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> ProcessingJob:
        job = await self._get_owned(job_id, workspace_id=workspace_id)
        if job.status not in (
            ProcessingJobStatus.PENDING.value,
            ProcessingJobStatus.RUNNING.value,
        ):
            raise ValidationException(
                f"Only a pending or running job can be cancelled (current status: "
                f"'{job.status}')."
            )
        job.status = ProcessingJobStatus.CANCELLED.value
        await self._jobs.update(job)
        return job
