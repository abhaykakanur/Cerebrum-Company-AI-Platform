"""``ChunkingService``: CIS Phase 2 Prompt 4's Chunking Engine —
dispatches a completed
:class:`~cerebrum.infrastructure.database.models.document_extraction.DocumentExtraction`'s
normalized text to the chosen
cerebrum.infrastructure.chunking.registry strategy, and persists the
result as an ordered set of
:class:`~cerebrum.infrastructure.database.models.chunk.Chunk` rows.

Runs synchronously within the request that triggers it — same
"no worker consumes a queue yet" reasoning as
cerebrum.application.knowledge.extraction_service.ExtractionService,
whose ``ProcessingJob``-per-run pattern this mirrors exactly (one
``CHUNKING`` job per call, real status/progress, no separate
job-lifecycle code needed for
cerebrum.api.v1.processing_jobs's existing status/cancel/history
endpoints to keep working).

Re-chunking a version (calling :meth:`chunk_version` again, with the
same or a different strategy) replaces its entire prior
:class:`~cerebrum.infrastructure.database.models.chunk.Chunk` set —
chunks are not versioned/kept across strategy changes, since a stale
chunk set from a different strategy or an outdated extraction would be
actively misleading to a future consumer (Phase 3's embedding
pipeline).
"""

import asyncio
import uuid

from cerebrum.infrastructure.chunking.options import ChunkingOptions
from cerebrum.infrastructure.chunking.registry import build_chunker_registry
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.document_extraction import (
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_extraction_repository import (
    DocumentExtractionRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException


class ChunkingService:
    def __init__(
        self,
        *,
        chunk_repository: ChunkRepository,
        extraction_repository: DocumentExtractionRepository,
        version_repository: DocumentVersionRepository,
        document_repository: DocumentRepository,
        job_repository: ProcessingJobRepository,
    ) -> None:
        self._chunks = chunk_repository
        self._extractions = extraction_repository
        self._versions = version_repository
        self._documents = document_repository
        self._jobs = job_repository
        self._chunkers = build_chunker_registry()

    async def list_chunks(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[Chunk]:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        return await self._chunks.list_by_document_version(document_version_id)

    async def chunk_version(
        self,
        document_version_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        strategy: ChunkingStrategy,
        options: ChunkingOptions | None = None,
    ) -> ProcessingJob:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        extraction = await self._extractions.get_by_version(document_version_id)
        if extraction is None or extraction.status != ExtractionStatus.COMPLETED.value:
            raise ValidationException(
                f"Document version {document_version_id} has no completed "
                f"extraction to chunk."
            )

        job = ProcessingJob(
            document_version_id=document_version_id,
            job_type=ProcessingJobType.CHUNKING.value,
            status=ProcessingJobStatus.RUNNING.value,
            progress_percent=10,
        )
        await self._jobs.add(job)

        await self._chunks.delete_by_document_version(document_version_id)

        chunker = self._chunkers[strategy]
        try:
            specs = await asyncio.to_thread(
                chunker.chunk,
                extraction.extracted_text or "",
                options or ChunkingOptions(),
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 - a strategy failure is a job failure, not a crash
            job.status = ProcessingJobStatus.FAILED.value
            job.error_message = str(exc)
            job.progress_percent = 0
            await self._jobs.update(job)
            return job

        job.progress_percent = 60
        await self._jobs.update(job)

        chunks = [
            await self._chunks.add(
                Chunk(
                    document_version_id=document_version_id,
                    extraction_id=extraction.id,
                    processing_job_id=job.id,
                    strategy=strategy.value,
                    chunk_index=index,
                    text=spec.text,
                    character_count=len(spec.text),
                    start_offset=spec.start_offset,
                    end_offset=spec.end_offset,
                    overlap_with_previous=spec.overlap_with_previous,
                    chunk_metadata=spec.metadata,
                )
            )
            for index, spec in enumerate(specs)
        ]
        for index, spec in enumerate(specs):
            if spec.parent_index is not None:
                chunks[index].parent_chunk_id = chunks[spec.parent_index].id
                await self._chunks.update(chunks[index])

        job.status = ProcessingJobStatus.COMPLETED.value
        job.progress_percent = 100
        await self._jobs.update(job)
        return job

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
