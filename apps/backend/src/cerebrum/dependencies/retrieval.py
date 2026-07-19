"""FastAPI DI providers for CIS Phase 3 Prompt 3's Retrieval Engine,
Context Builder & Explainability services. Mirrors
cerebrum.dependencies.semantic's exact pattern: each provider composes
already-established providers (``get_hybrid_search_service``,
``get_knowledge_graph_service``, ``get_search_service``) rather than
re-building their underlying repositories.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.application.retrieval.citation_service import CitationService
from cerebrum.application.retrieval.context_builder_service import (
    ContextBuilderService,
)
from cerebrum.application.retrieval.explainability_service import (
    ExplainabilityService,
)
from cerebrum.application.retrieval.ranking_service import RankingService
from cerebrum.application.retrieval.retrieval_service import RetrievalService
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    Neo4jDep,
    OpenSearchDep,
    QdrantDep,
)
from cerebrum.dependencies.knowledge_graph import get_knowledge_graph_service
from cerebrum.dependencies.semantic import (
    get_hybrid_search_service,
    get_search_service,
)
from cerebrum.repositories.postgres.chunk_repository import ChunkRepository
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
)


def get_retrieval_service(
    session: DbSessionDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    neo4j_driver: Neo4jDep,
    event_dispatcher: EventDispatcherDep,
) -> RetrievalService:
    return RetrievalService(
        hybrid_search_service=get_hybrid_search_service(
            session, qdrant_client, opensearch_client, event_dispatcher
        ),
        knowledge_graph_service=get_knowledge_graph_service(
            session, neo4j_driver, event_dispatcher
        ),
        search_service=get_search_service(session, opensearch_client, event_dispatcher),
        event_dispatcher=event_dispatcher,
    )


def get_ranking_service() -> RankingService:
    return RankingService()


def get_context_builder_service(
    session: DbSessionDep,
    neo4j_driver: Neo4jDep,
    event_dispatcher: EventDispatcherDep,
) -> ContextBuilderService:
    return ContextBuilderService(
        chunk_repository=ChunkRepository(session),
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        relationship_service=RelationshipService(
            relationship_repository=RelationshipRepository(session)
        ),
        document_repository=DocumentRepository(session),
        version_repository=DocumentVersionRepository(session),
        knowledge_graph_service=get_knowledge_graph_service(
            session, neo4j_driver, event_dispatcher
        ),
        event_dispatcher=event_dispatcher,
    )


def get_citation_service(
    session: DbSessionDep,
    event_dispatcher: EventDispatcherDep,
) -> CitationService:
    return CitationService(
        document_repository=DocumentRepository(session),
        version_repository=DocumentVersionRepository(session),
        chunk_repository=ChunkRepository(session),
        entity_service=EntityService(entity_repository=EntityRepository(session)),
        event_dispatcher=event_dispatcher,
    )


def get_explainability_service() -> ExplainabilityService:
    return ExplainabilityService()


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
RankingServiceDep = Annotated[RankingService, Depends(get_ranking_service)]
ContextBuilderServiceDep = Annotated[
    ContextBuilderService, Depends(get_context_builder_service)
]
CitationServiceDep = Annotated[CitationService, Depends(get_citation_service)]
ExplainabilityServiceDep = Annotated[
    ExplainabilityService, Depends(get_explainability_service)
]
