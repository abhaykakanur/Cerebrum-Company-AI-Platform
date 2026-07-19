"""FastAPI DI providers for CIS Phase 3 Prompt 2's Semantic Intelligence
services. Mirrors cerebrum.dependencies.knowledge_graph's exact
pattern: each provider constructs a fresh, request-scoped service from
the already-established
:data:`~cerebrum.dependencies.database.DbSessionDep`,
:data:`~cerebrum.dependencies.infrastructure.QdrantDep`, and
:data:`~cerebrum.dependencies.infrastructure.OpenSearchDep`.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.semantic.embedding_service import EmbeddingService
from cerebrum.application.semantic.hybrid_search_service import HybridSearchService
from cerebrum.application.semantic.search_service import SearchService
from cerebrum.application.semantic.vector_index_service import VectorIndexService
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    OpenSearchDep,
    QdrantDep,
)
from cerebrum.infrastructure.embeddings.providers import HashingEmbeddingProvider
from cerebrum.repositories.opensearch.search_index_repository import (
    SearchIndexRepository,
)
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
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.processing_job_repository import (
    ProcessingJobRepository,
)
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository
from cerebrum.repositories.qdrant.vector_repository import VectorRepository

_EMBEDDING_DIMENSION = 256


def get_embedding_provider() -> HashingEmbeddingProvider:
    return HashingEmbeddingProvider(dimension=_EMBEDDING_DIMENSION)


def get_vector_index_service(
    session: DbSessionDep, qdrant_client: QdrantDep
) -> VectorIndexService:
    return VectorIndexService(
        vector_repository=VectorRepository(
            qdrant_client, vector_size=_EMBEDDING_DIMENSION
        )
    )


def get_search_service(
    session: DbSessionDep,
    opensearch_client: OpenSearchDep,
    event_dispatcher: EventDispatcherDep,
) -> SearchService:
    return SearchService(
        search_index_repository=SearchIndexRepository(opensearch_client),
        event_dispatcher=event_dispatcher,
    )


def get_embedding_service(
    session: DbSessionDep,
    qdrant_client: QdrantDep,
    event_dispatcher: EventDispatcherDep,
) -> EmbeddingService:
    return EmbeddingService(
        provider=get_embedding_provider(),
        vector_index_service=get_vector_index_service(session, qdrant_client),
        chunk_repository=ChunkRepository(session),
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        relationship_service=RelationshipService(
            relationship_repository=RelationshipRepository(session)
        ),
        extraction_repository=DocumentExtractionRepository(session),
        metadata_repository=DocumentMetadataRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        job_repository=ProcessingJobRepository(session),
        event_dispatcher=event_dispatcher,
    )


def get_hybrid_search_service(
    session: DbSessionDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    event_dispatcher: EventDispatcherDep,
) -> HybridSearchService:
    return HybridSearchService(
        provider=get_embedding_provider(),
        vector_index_service=get_vector_index_service(session, qdrant_client),
        search_service=get_search_service(session, opensearch_client, event_dispatcher),
    )


VectorIndexServiceDep = Annotated[VectorIndexService, Depends(get_vector_index_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
HybridSearchServiceDep = Annotated[
    HybridSearchService, Depends(get_hybrid_search_service)
]
