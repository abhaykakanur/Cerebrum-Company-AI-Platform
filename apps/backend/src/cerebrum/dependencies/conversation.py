"""FastAPI DI providers for CIS Phase 4 Prompt 2's Conversational AI,
Memory & Intelligent Sessions. Mirrors cerebrum.dependencies.ai's exact
pattern: ``get_session_service`` composes already-established providers
(``get_rag_service``) rather than re-building CIS Phase 4 Prompt 1's
retrieval/prompt/response service chain.
"""

from typing import Annotated

from fastapi import Depends

from cerebrum.application.conversation.conversation_service import (
    ConversationService,
)
from cerebrum.application.conversation.conversation_summary_service import (
    ConversationSummaryService,
)
from cerebrum.application.conversation.memory_service import MemoryService
from cerebrum.application.conversation.session_service import SessionService
from cerebrum.dependencies.ai import get_rag_service
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    Neo4jDep,
    OpenSearchDep,
    QdrantDep,
    RedisDep,
)
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository


def get_conversation_repository(session: DbSessionDep) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(session: DbSessionDep) -> MessageRepository:
    return MessageRepository(session)


def get_conversation_service(
    session: DbSessionDep, event_dispatcher: EventDispatcherDep
) -> ConversationService:
    return ConversationService(
        conversation_repository=get_conversation_repository(session),
        message_repository=get_message_repository(session),
        event_dispatcher=event_dispatcher,
    )


def get_memory_service(session: DbSessionDep) -> MemoryService:
    return MemoryService(
        conversation_repository=get_conversation_repository(session),
        message_repository=get_message_repository(session),
    )


def get_conversation_summary_service(
    session: DbSessionDep, event_dispatcher: EventDispatcherDep
) -> ConversationSummaryService:
    return ConversationSummaryService(
        conversation_repository=get_conversation_repository(session),
        message_repository=get_message_repository(session),
        event_dispatcher=event_dispatcher,
    )


def get_session_service(
    session: DbSessionDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    neo4j_driver: Neo4jDep,
    redis: RedisDep,
    event_dispatcher: EventDispatcherDep,
) -> SessionService:
    return SessionService(
        conversation_service=get_conversation_service(session, event_dispatcher),
        memory_service=get_memory_service(session),
        summary_service=get_conversation_summary_service(session, event_dispatcher),
        rag_service=get_rag_service(
            session,
            qdrant_client,
            opensearch_client,
            neo4j_driver,
            redis,
            event_dispatcher,
        ),
    )


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
ConversationSummaryServiceDep = Annotated[
    ConversationSummaryService, Depends(get_conversation_summary_service)
]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
