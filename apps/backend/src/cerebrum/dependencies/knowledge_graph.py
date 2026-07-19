"""FastAPI DI providers for CIS Phase 3 Prompt 1's Knowledge Graph &
Entity Intelligence services. Mirrors
cerebrum.dependencies.knowledge's exact pattern: each provider
constructs a fresh, request-scoped service from the already-established
:data:`~cerebrum.dependencies.database.DbSessionDep` and
:data:`~cerebrum.dependencies.infrastructure.Neo4jDep`.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import EventDispatcherDep, Neo4jDep
from cerebrum.infrastructure.entities.extractors import (
    CompositeEntityExtractor,
    DictionaryEntityExtractor,
    RegexEntityExtractor,
)
from cerebrum.infrastructure.relationships.extractors import (
    CueBasedRelationshipExtractor,
)
from cerebrum.repositories.neo4j.knowledge_graph_repository import (
    KnowledgeGraphRepository,
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
from cerebrum.repositories.postgres.workspace_repository import WorkspaceRepository


def get_entity_service(session: DbSessionDep) -> EntityService:
    return EntityService(entity_repository=EntityRepository(session))


def get_relationship_service(session: DbSessionDep) -> RelationshipService:
    return RelationshipService(relationship_repository=RelationshipRepository(session))


def get_knowledge_graph_service(
    session: DbSessionDep,
    neo4j_driver: Neo4jDep,
    event_dispatcher: EventDispatcherDep,
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        entity_service=get_entity_service(session),
        relationship_service=get_relationship_service(session),
        graph_repository=KnowledgeGraphRepository(neo4j_driver),
        chunk_repository=ChunkRepository(session),
        version_repository=DocumentVersionRepository(session),
        document_repository=DocumentRepository(session),
        workspace_repository=WorkspaceRepository(session),
        entity_extractor=CompositeEntityExtractor(
            [RegexEntityExtractor(), DictionaryEntityExtractor()]
        ),
        relationship_extractor=CueBasedRelationshipExtractor(),
        event_dispatcher=event_dispatcher,
    )


EntityServiceDep = Annotated[EntityService, Depends(get_entity_service)]
RelationshipServiceDep = Annotated[
    RelationshipService, Depends(get_relationship_service)
]
KnowledgeGraphServiceDep = Annotated[
    KnowledgeGraphService, Depends(get_knowledge_graph_service)
]
