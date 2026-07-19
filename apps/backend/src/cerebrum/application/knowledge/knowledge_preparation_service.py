"""``KnowledgePreparationService``: CIS Phase 2 Prompt 4's Processing
Orchestration — runs the pipeline
(cerebrum.application.knowledge.extraction_service.ExtractionService,
then cerebrum.application.knowledge.chunking_service.ChunkingService,
then — CIS Phase 3 Prompt 1 —
cerebrum.application.knowledge_graph.knowledge_graph_service.KnowledgeGraphService,
then — CIS Phase 3 Prompt 2 —
cerebrum.application.semantic.embedding_service.EmbeddingService and
cerebrum.application.semantic.search_service.SearchService)
against a document version end to end, tracks aggregate progress across
stages, builds/updates the
:class:`~cerebrum.infrastructure.database.models.document_manifest.DocumentManifest`,
and emits :class:`~cerebrum.application.knowledge.events.DocumentKnowledgePreparedEvent`
on success — the pipeline's "Semantic Ready" terminal state.

Composes the existing services rather than duplicating their
repositories/logic — :meth:`prepare` is this milestone's Reprocess
entry point (the ambiguity is deliberate: "run the pipeline" and
"run it again" are the same operation here, since nothing runs
asynchronously in the background yet — see the composed services' own
docstrings). ``force=False`` (the default) skips a stage whose prior
run already succeeded, which is also how a caller resumes after a
mid-pipeline failure: retrying :meth:`prepare` re-runs only the stage
that failed, not the one that already completed. The graph, embedding,
and search-indexing stages always run when the stage before them
succeeds — each one's own idempotent-by-deterministic-ID/version-aware
supersede logic (see ``KnowledgeGraphService``/``EmbeddingService``/
``SearchIndexRepository``'s own docstrings) already makes a repeated
call safe, so none of them needs a separate "already done" check here.
"""

import uuid
from dataclasses import dataclass

from cerebrum.application.knowledge.chunking_service import ChunkingService
from cerebrum.application.knowledge.events import DocumentKnowledgePreparedEvent
from cerebrum.application.knowledge.extraction_service import ExtractionService
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from cerebrum.application.semantic.embedding_service import EmbeddingService
from cerebrum.application.semantic.search_service import SearchService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.chunk import Chunk, ChunkingStrategy
from cerebrum.infrastructure.database.models.document_extraction import (
    ExtractionStatus,
)
from cerebrum.infrastructure.database.models.document_manifest import (
    DocumentManifest,
    ManifestStatus,
)
from cerebrum.infrastructure.database.models.document_version import DocumentVersion
from cerebrum.infrastructure.database.models.processing_job import (
    ProcessingJob,
    ProcessingJobStatus,
)
from cerebrum.repositories.postgres.document_extraction_repository import (
    DocumentExtractionRepository,
)
from cerebrum.repositories.postgres.document_manifest_repository import (
    DocumentManifestRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.shared.errors.exceptions import NotFoundException

_DEFAULT_STRATEGY = ChunkingStrategy.RECURSIVE
_STAGE_COUNT = 2
"""Extraction, then Chunking — used only to average the two stages'
``progress_percent`` into one overall number for :meth:`get_progress`.
"""


@dataclass(frozen=True, slots=True)
class PipelineProgress:
    extraction_status: str | None
    extraction_progress_percent: int
    chunking_status: str | None
    chunking_progress_percent: int
    overall_progress_percent: int


class KnowledgePreparationService:
    def __init__(
        self,
        *,
        extraction_service: ExtractionService,
        chunking_service: ChunkingService,
        graph_service: KnowledgeGraphService,
        embedding_service: EmbeddingService,
        search_service: SearchService,
        entity_service: EntityService,
        manifest_repository: DocumentManifestRepository,
        extraction_repository: DocumentExtractionRepository,
        job_repository: ProcessingJobRepository,
        version_repository: DocumentVersionRepository,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._extraction_service = extraction_service
        self._chunking_service = chunking_service
        self._graph_service = graph_service
        self._embedding_service = embedding_service
        self._search_service = search_service
        self._entity_service = entity_service
        self._manifests = manifest_repository
        self._extractions = extraction_repository
        self._jobs = job_repository
        self._versions = version_repository
        self._documents = document_repository
        self._workspaces = workspace_repository
        self._events = event_dispatcher

    async def prepare(
        self,
        document_version_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        strategy: ChunkingStrategy = _DEFAULT_STRATEGY,
        force: bool = False,
    ) -> DocumentManifest:
        version = await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )

        extraction = await self._extractions.get_by_version(document_version_id)
        if (
            force
            or extraction is None
            or extraction.status != ExtractionStatus.COMPLETED.value
        ):
            extraction = await self._extraction_service.extract(
                document_version_id, workspace_id=workspace_id
            )

        if extraction.status != ExtractionStatus.COMPLETED.value:
            return await self._save_manifest(
                document_version_id,
                extraction_id=extraction.id,
                status=ManifestStatus.FAILED,
                strategy=None,
                chunks=[],
                error_message=extraction.error_message
                or f"Extraction did not complete (status: '{extraction.status}').",
            )

        chunk_job = await self._chunking_service.chunk_version(
            document_version_id, workspace_id=workspace_id, strategy=strategy
        )
        if chunk_job.status != ProcessingJobStatus.COMPLETED.value:
            return await self._save_manifest(
                document_version_id,
                extraction_id=extraction.id,
                status=ManifestStatus.FAILED,
                strategy=strategy.value,
                chunks=[],
                error_message=chunk_job.error_message or "Chunking did not complete.",
            )

        chunks = await self._chunking_service.list_chunks(
            document_version_id, workspace_id=workspace_id
        )

        graph_result = await self._graph_service.process_version(
            document_version_id, workspace_id=workspace_id
        )

        embedding_job = await self._embedding_service.embed_version(
            document_version_id, workspace_id=workspace_id, force=force
        )
        if embedding_job.status != ProcessingJobStatus.COMPLETED.value:
            return await self._save_manifest(
                document_version_id,
                extraction_id=extraction.id,
                status=ManifestStatus.FAILED,
                strategy=strategy.value,
                chunks=chunks,
                error_message=embedding_job.error_message
                or "Embedding generation did not complete.",
                entity_count=graph_result.entity_count,
                relationship_count=graph_result.relationship_count,
            )

        document = await self._documents.get_by_id(version.document_id)
        assert document is not None  # validated by _require_version_in_workspace above
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundException(f"No workspace with id {workspace_id}.")
        entities = await self._entity_service.list_by_source_chunks(
            [chunk.id for chunk in chunks], workspace_id=workspace_id
        )
        indexed_count = await self._search_service.index_version(
            document=document,
            document_version_id=document_version_id,
            chunks=chunks,
            entities=entities,
            workspace_id=workspace_id,
            organization_id=workspace.organization_id,
        )

        manifest = await self._save_manifest(
            document_version_id,
            extraction_id=extraction.id,
            status=ManifestStatus.READY,
            strategy=strategy.value,
            chunks=chunks,
            error_message=None,
            entity_count=graph_result.entity_count,
            relationship_count=graph_result.relationship_count,
            indexed_count=indexed_count,
        )
        self._events.publish(
            DocumentKnowledgePreparedEvent(
                document_version_id=document_version_id,
                workspace_id=workspace_id,
                chunk_count=len(chunks),
                chunking_strategy=strategy.value,
            )
        )
        return manifest

    async def get_manifest(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> DocumentManifest:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        manifest = await self._manifests.get_by_version(document_version_id)
        if manifest is None:
            raise NotFoundException(
                f"No manifest for document version {document_version_id}."
            )
        return manifest

    async def get_progress(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> PipelineProgress:
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        jobs = await self._jobs.list_by_document_version(document_version_id)
        extraction_job = self._latest_job(jobs, {"parsing", "ocr"})
        chunking_job = self._latest_job(jobs, {"chunking"})
        extraction_progress = extraction_job.progress_percent if extraction_job else 0
        chunking_progress = chunking_job.progress_percent if chunking_job else 0
        return PipelineProgress(
            extraction_status=extraction_job.status if extraction_job else None,
            extraction_progress_percent=extraction_progress,
            chunking_status=chunking_job.status if chunking_job else None,
            chunking_progress_percent=chunking_progress,
            overall_progress_percent=(extraction_progress + chunking_progress)
            // _STAGE_COUNT,
        )

    async def cancel(
        self, document_version_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> int:
        """Cancels every ``PENDING``/``RUNNING`` job for this version —
        in practice this mostly reaches jobs created via
        cerebrum.application.knowledge.processing_service.ProcessingService.enqueue
        (which never auto-executes; see that service's docstring), since
        this service's own :meth:`prepare` runs each stage to completion
        before returning. Returns the number of jobs cancelled.
        """
        await self._require_version_in_workspace(
            document_version_id, workspace_id=workspace_id
        )
        jobs = await self._jobs.list_by_document_version(document_version_id)
        cancelled = 0
        for job in jobs:
            if job.status in (
                ProcessingJobStatus.PENDING.value,
                ProcessingJobStatus.RUNNING.value,
            ):
                job.status = ProcessingJobStatus.CANCELLED.value
                await self._jobs.update(job)
                cancelled += 1
        return cancelled

    async def _save_manifest(
        self,
        document_version_id: uuid.UUID,
        *,
        extraction_id: uuid.UUID | None,
        status: ManifestStatus,
        strategy: str | None,
        chunks: list[Chunk],
        error_message: str | None,
        entity_count: int = 0,
        relationship_count: int = 0,
        indexed_count: int = 0,
    ) -> DocumentManifest:
        character_counts = [chunk.character_count for chunk in chunks]
        statistics = (
            {
                "avg_chunk_size": sum(character_counts) // len(character_counts),
                "min_chunk_size": min(character_counts),
                "max_chunk_size": max(character_counts),
            }
            if character_counts
            else {}
        )
        if entity_count or relationship_count:
            statistics = {
                **statistics,
                "entity_count": entity_count,
                "relationship_count": relationship_count,
            }
        if indexed_count:
            statistics = {**statistics, "indexed_count": indexed_count}
        existing = await self._manifests.get_by_version(document_version_id)
        if existing is not None:
            existing.extraction_id = extraction_id
            existing.status = status.value
            existing.chunking_strategy = strategy
            existing.chunk_count = len(chunks)
            existing.total_character_count = sum(character_counts)
            existing.statistics = statistics
            existing.error_message = error_message
            return await self._manifests.update(existing)
        return await self._manifests.add(
            DocumentManifest(
                document_version_id=document_version_id,
                extraction_id=extraction_id,
                status=status.value,
                chunking_strategy=strategy,
                chunk_count=len(chunks),
                total_character_count=sum(character_counts),
                statistics=statistics,
                error_message=error_message,
            )
        )

    @staticmethod
    def _latest_job(
        jobs: list[ProcessingJob], job_types: set[str]
    ) -> ProcessingJob | None:
        matching = [job for job in jobs if job.job_type in job_types]
        return max(matching, key=lambda job: job.created_at) if matching else None

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
