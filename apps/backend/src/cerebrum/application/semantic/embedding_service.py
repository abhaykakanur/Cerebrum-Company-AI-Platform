"""``EmbeddingService``: CIS Phase 3 Prompt 2's Embedding Pipeline —
generates embeddings for a document version's chunks, entity
descriptions, relationship descriptions, a truncation-based document
summary, and a synthesized metadata string, storing each via
:class:`~cerebrum.application.semantic.vector_index_service.VectorIndexService`.

Tracks status/progress/retry via the same
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
mechanism (job type ``EMBEDDINGS``, already named in CIS Phase 2
Prompt 2's ``ProcessingJobType``) every earlier pipeline stage since
CIS Phase 2 Prompt 3 has used — runs synchronously within the request
that triggers it, no background worker consumes a queue yet (same
reasoning every composed stage's own docstring gives).

**Incremental updates**: each artifact is skipped (not re-embedded)
when
:meth:`~cerebrum.application.semantic.vector_index_service.VectorIndexService.is_current`
reports its existing vector is already at the current
``embedding_model``'s version — ``force=True`` bypasses this and
re-embeds everything, CIS Phase 3 Prompt 2's Regeneration.

**Document summary**: a real, non-LLM summary — the extracted text's
first :data:`_SUMMARY_CHARACTER_LIMIT` characters, honestly a
truncation rather than an abstractive summary (LLM-based summarization
is out of scope — see this milestone's "DO NOT IMPLEMENT: LLM calls").
"""

import uuid
from typing import Any

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.semantic.events import (
    EmbeddingsGeneratedEvent,
    VectorIndexUpdatedEvent,
)
from cerebrum.application.semantic.vector_index_service import VectorIndexService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.document_extraction import (
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from cerebrum.infrastructure.embeddings.kind import EmbeddingKind
from cerebrum.infrastructure.embeddings.providers import EmbeddingProvider
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
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
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

_SUMMARY_CHARACTER_LIMIT = 500


class EmbeddingService:
    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        vector_index_service: VectorIndexService,
        chunk_repository: ChunkRepository,
        entity_service: EntityService,
        relationship_service: RelationshipService,
        extraction_repository: DocumentExtractionRepository,
        metadata_repository: DocumentMetadataRepository,
        version_repository: DocumentVersionRepository,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        job_repository: ProcessingJobRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._provider = provider
        self._vectors = vector_index_service
        self._chunks = chunk_repository
        self._entities = entity_service
        self._relationships = relationship_service
        self._extractions = extraction_repository
        self._metadata = metadata_repository
        self._versions = version_repository
        self._documents = document_repository
        self._workspaces = workspace_repository
        self._jobs = job_repository
        self._events = event_dispatcher

    async def embed_version(
        self,
        document_version_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        force: bool = False,
    ) -> ProcessingJob:
        job = ProcessingJob(
            document_version_id=document_version_id,
            job_type=ProcessingJobType.EMBEDDINGS.value,
            status=ProcessingJobStatus.RUNNING.value,
        )
        await self._jobs.add(job)
        return await self._run(job, workspace_id=workspace_id, force=force)

    async def retry(
        self, job_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> ProcessingJob:
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
        job.retry_count += 1
        job.status = ProcessingJobStatus.RUNNING.value
        job.error_message = None
        job.progress_percent = 0
        await self._jobs.update(job)
        return await self._run(job, workspace_id=workspace_id, force=True)

    async def _run(
        self, job: ProcessingJob, *, workspace_id: uuid.UUID, force: bool
    ) -> ProcessingJob:
        """Runs (or re-runs, for :meth:`retry`) ``job`` in place —
        never creates a second ``ProcessingJob`` row for a retry, so
        ``job.retry_count`` (already incremented by the caller when
        this is a retry) survives on the same row that's returned.
        """
        document_version_id = job.document_version_id
        version = await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundException(f"No workspace with id {workspace_id}.")

        try:
            embedded_count = await self._embed_all_artifacts(
                document_version_id,
                document_id=version.document_id,
                workspace_id=workspace_id,
                organization_id=workspace.organization_id,
                job=job,
                force=force,
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 - a provider/storage failure is a job failure, not a crash
            job.status = ProcessingJobStatus.FAILED.value
            job.error_message = str(exc)
            job.progress_percent = 0
            await self._jobs.update(job)
            return job

        job.status = ProcessingJobStatus.COMPLETED.value
        job.progress_percent = 100
        await self._jobs.update(job)
        self._events.publish(
            EmbeddingsGeneratedEvent(
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                embedding_count=embedded_count,
                embedding_model=self._provider.model_name,
            )
        )
        self._events.publish(
            VectorIndexUpdatedEvent(
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                vector_count=embedded_count,
            )
        )
        return job

    async def _embed_all_artifacts(
        self,
        document_version_id: uuid.UUID,
        *,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        job: ProcessingJob,
        force: bool,
    ) -> int:
        embedded_count = 0

        chunks = await self._chunks.list_by_document_version(document_version_id)
        chunk_ids = [chunk.id for chunk in chunks]
        for chunk in chunks:
            embedded_count += await self._embed_one(
                kind=EmbeddingKind.CHUNK.value,
                source_id=chunk.id,
                text=chunk.text,
                chunk_id=chunk.id,
                entity_id=None,
                document_id=document_id,
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                organization_id=organization_id,
                metadata={"chunk_index": chunk.chunk_index},
                force=force,
            )

        entities = await self._entities.list_by_source_chunks(
            chunk_ids, workspace_id=workspace_id
        )
        for entity in entities:
            text = entity.description or entity.canonical_name
            embedded_count += await self._embed_one(
                kind=EmbeddingKind.ENTITY_DESCRIPTION.value,
                source_id=entity.id,
                text=text,
                chunk_id=entity.source_chunk_id,
                entity_id=entity.id,
                document_id=document_id,
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                organization_id=organization_id,
                metadata={"entity_type": entity.entity_type},
                force=force,
            )

        relationships = await self._relationships.list_by_source_chunks(
            chunk_ids, workspace_id=workspace_id
        )
        for relationship in relationships:
            if not relationship.evidence:
                continue
            embedded_count += await self._embed_one(
                kind=EmbeddingKind.RELATIONSHIP_DESCRIPTION.value,
                source_id=relationship.id,
                text=relationship.evidence,
                chunk_id=relationship.source_chunk_id,
                entity_id=None,
                document_id=document_id,
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                organization_id=organization_id,
                metadata={"relationship_type": relationship.relationship_type},
                force=force,
            )

        job.progress_percent = 70
        await self._jobs.update(job)

        extraction = await self._extractions.get_by_version(document_version_id)
        if (
            extraction is not None
            and extraction.status == ExtractionStatus.COMPLETED.value
        ):
            summary_text = (extraction.extracted_text or "")[:_SUMMARY_CHARACTER_LIMIT]
            if summary_text.strip():
                embedded_count += await self._embed_one(
                    kind=EmbeddingKind.DOCUMENT_SUMMARY.value,
                    source_id=document_version_id,
                    text=summary_text,
                    chunk_id=None,
                    entity_id=None,
                    document_id=document_id,
                    document_version_id=document_version_id,
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                    metadata={"character_limit": _SUMMARY_CHARACTER_LIMIT},
                    force=force,
                )

        metadata_record = await self._metadata.get_by_version(document_version_id)
        if metadata_record is not None:
            document = await self._documents.get_by_id(document_id)
            metadata_text = " ".join(
                part
                for part in (
                    document.name if document else None,
                    metadata_record.original_filename,
                    metadata_record.mime_type,
                )
                if part
            )
            embedded_count += await self._embed_one(
                kind=EmbeddingKind.METADATA.value,
                source_id=document_version_id,
                text=metadata_text,
                chunk_id=None,
                entity_id=None,
                document_id=document_id,
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                organization_id=organization_id,
                metadata={"mime_type": metadata_record.mime_type},
                force=force,
            )

        job.progress_percent = 90
        await self._jobs.update(job)
        return embedded_count

    async def _embed_one(
        self,
        *,
        kind: str,
        source_id: uuid.UUID,
        text: str,
        chunk_id: uuid.UUID | None,
        entity_id: uuid.UUID | None,
        document_id: uuid.UUID,
        document_version_id: uuid.UUID,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        metadata: dict[str, Any],
        force: bool,
    ) -> int:
        if not text.strip():
            return 0
        embedding_version = self._provider.model_name
        if not force and await self._vectors.is_current(
            kind=kind, source_id=source_id, embedding_version=embedding_version
        ):
            return 0
        vector = self._provider.embed([text])[0]
        await self._vectors.upsert(
            kind=kind,
            source_id=source_id,
            vector=vector,
            chunk_id=chunk_id,
            entity_id=entity_id,
            document_id=document_id,
            document_version_id=document_version_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            embedding_model=self._provider.model_name,
            embedding_version=embedding_version,
            metadata=metadata,
            provenance={"source_text_length": len(text)},
        )
        return 1

    async def _require_version_in_workspace(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> DocumentVersion:
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
        return version
