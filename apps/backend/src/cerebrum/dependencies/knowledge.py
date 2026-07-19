"""FastAPI DI providers for the Knowledge Domain's application services
— CIS Phase 2 Prompt 1. Mirrors cerebrum.dependencies.auth's exact
pattern: each provider constructs a fresh, request-scoped service from
the already-established :data:`~cerebrum.dependencies.database.DbSessionDep`.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.knowledge.chunking_service import ChunkingService
from cerebrum.application.knowledge.collection_service import CollectionService
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.extraction_service import ExtractionService
from cerebrum.application.knowledge.folder_service import FolderService
from cerebrum.application.knowledge.knowledge_preparation_service import (
    KnowledgePreparationService,
)
from cerebrum.application.knowledge.label_service import LabelService
from cerebrum.application.knowledge.metadata_service import MetadataService
from cerebrum.application.knowledge.organization_service import OrganizationService
from cerebrum.application.knowledge.processing_service import ProcessingService
from cerebrum.application.knowledge.tag_service import TagService
from cerebrum.application.knowledge.upload_service import UploadService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.application.knowledge.workspace_service import WorkspaceService
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    MinIODep,
    Neo4jDep,
    OpenSearchDep,
    QdrantDep,
    RedisDep,
)
from cerebrum.dependencies.knowledge_graph import get_knowledge_graph_service
from cerebrum.dependencies.semantic import get_embedding_service, get_search_service
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.queue.redis_queue import RedisQueue
from cerebrum.infrastructure.security.virus_scan import NoOpVirusScanner
from cerebrum.infrastructure.storage.minio_files import (
    MinIOFileDownloader,
    MinIOFileUploader,
)
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.collection_repository import CollectionRepository
from cerebrum.repositories.postgres.document_extraction_repository import (
    DocumentExtractionRepository,
)
from cerebrum.repositories.postgres.document_manifest_repository import (
    DocumentManifestRepository,
)
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.organization_repository import (
    OrganizationRepository,
)
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.tag_repository import TagRepository
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository


def get_organization_service(session: DbSessionDep) -> OrganizationService:
    return OrganizationService(OrganizationRepository(session))


def get_workspace_service(session: DbSessionDep) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(session))


def get_folder_service(session: DbSessionDep) -> FolderService:
    return FolderService(FolderRepository(session))


def get_document_service(session: DbSessionDep) -> DocumentService:
    return DocumentService(
        document_repository=DocumentRepository(session),
        folder_repository=FolderRepository(session),
        tag_repository=TagRepository(session),
        label_repository=LabelRepository(session),
    )


def get_version_service(session: DbSessionDep) -> VersionService:
    return VersionService(
        version_repository=DocumentVersionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        document_repository=DocumentRepository(session),
    )


def get_metadata_service(session: DbSessionDep) -> MetadataService:
    return MetadataService(
        metadata_repository=DocumentMetadataRepository(session),
        version_repository=DocumentVersionRepository(session),
    )


def get_tag_service(session: DbSessionDep) -> TagService:
    return TagService(TagRepository(session))


def get_label_service(session: DbSessionDep) -> LabelService:
    return LabelService(LabelRepository(session))


def get_collection_service(session: DbSessionDep) -> CollectionService:
    return CollectionService(
        collection_repository=CollectionRepository(session),
        document_repository=DocumentRepository(session),
    )


def get_upload_service(
    session: DbSessionDep, minio_client: MinIODep, settings: SettingsDep
) -> UploadService:
    return UploadService(
        version_service=get_version_service(session),
        document_repository=DocumentRepository(session),
        uploader=MinIOFileUploader(minio_client, bucket=settings.minio.bucket),
        virus_scanner=NoOpVirusScanner(),
        settings=settings.documents,
        audit_service=AuditService(AuditEventRepository(session)),
    )


def get_file_downloader(
    minio_client: MinIODep, settings: SettingsDep
) -> MinIOFileDownloader:
    return MinIOFileDownloader(minio_client, bucket=settings.minio.bucket)


def get_processing_service(
    session: DbSessionDep, redis_client: RedisDep
) -> ProcessingService:
    return ProcessingService(
        job_repository=ProcessingJobRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        queue=RedisQueue(redis_client),
    )


def get_extraction_service(
    session: DbSessionDep, minio_client: MinIODep, settings: SettingsDep
) -> ExtractionService:
    return ExtractionService(
        extraction_repository=DocumentExtractionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        job_repository=ProcessingJobRepository(session),
        downloader=MinIOFileDownloader(minio_client, bucket=settings.minio.bucket),
    )


def get_chunking_service(session: DbSessionDep) -> ChunkingService:
    return ChunkingService(
        chunk_repository=ChunkRepository(session),
        extraction_repository=DocumentExtractionRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        job_repository=ProcessingJobRepository(session),
    )


def get_knowledge_preparation_service(
    session: DbSessionDep,
    minio_client: MinIODep,
    neo4j_driver: Neo4jDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    settings: SettingsDep,
    event_dispatcher: EventDispatcherDep,
) -> KnowledgePreparationService:
    return KnowledgePreparationService(
        extraction_service=get_extraction_service(session, minio_client, settings),
        chunking_service=get_chunking_service(session),
        graph_service=get_knowledge_graph_service(
            session, neo4j_driver, event_dispatcher
        ),
        embedding_service=get_embedding_service(
            session, qdrant_client, event_dispatcher
        ),
        search_service=get_search_service(session, opensearch_client, event_dispatcher),
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        manifest_repository=DocumentManifestRepository(session),
        extraction_repository=DocumentExtractionRepository(session),
        job_repository=ProcessingJobRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        event_dispatcher=event_dispatcher,
    )


OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
FolderServiceDep = Annotated[FolderService, Depends(get_folder_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
VersionServiceDep = Annotated[VersionService, Depends(get_version_service)]
MetadataServiceDep = Annotated[MetadataService, Depends(get_metadata_service)]
TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
CollectionServiceDep = Annotated[CollectionService, Depends(get_collection_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
FileDownloaderDep = Annotated[MinIOFileDownloader, Depends(get_file_downloader)]
ProcessingServiceDep = Annotated[ProcessingService, Depends(get_processing_service)]
ExtractionServiceDep = Annotated[ExtractionService, Depends(get_extraction_service)]
ChunkingServiceDep = Annotated[ChunkingService, Depends(get_chunking_service)]
KnowledgePreparationServiceDep = Annotated[
    KnowledgePreparationService, Depends(get_knowledge_preparation_service)
]
