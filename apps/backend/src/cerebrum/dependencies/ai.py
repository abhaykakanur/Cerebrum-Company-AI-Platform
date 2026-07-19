"""FastAPI DI providers for CIS Phase 4 Prompt 1's Enterprise RAG
Engine & AI Orchestration. Mirrors cerebrum.dependencies.retrieval's
exact pattern: each provider composes already-established providers
(``get_retrieval_service``, ``get_context_builder_service``,
``get_citation_service``) rather than re-building their underlying
repositories. :func:`get_llm_provider` is the one dependency that also
declares its own ``Query`` parameter (``provider``) — see
cerebrum.dependencies.auth.get_current_workspace_id for the same
"a dependency function may declare its own request parameters"
precedent (there, a header; here, a query parameter) — so every route
using ``LLMProviderDep`` automatically exposes an optional
``?provider=`` override without repeating it in every route signature.
"""

from typing import Annotated

from fastapi import Depends, Query

from cerebrum.application.ai.ai_response_service import AIResponseService
from cerebrum.application.ai.prompt_builder_service import PromptBuilderService
from cerebrum.application.ai.rag_service import RAGService
from cerebrum.application.ai.usage_stats_service import AIUsageStatsService
from cerebrum.dependencies.database import DbSessionDep
from cerebrum.dependencies.infrastructure import (
    EventDispatcherDep,
    HttpClientDep,
    Neo4jDep,
    OpenSearchDep,
    QdrantDep,
    RedisDep,
)
from cerebrum.dependencies.retrieval import (
    get_citation_service,
    get_context_builder_service,
    get_retrieval_service,
)
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.llm.provider import LLMProvider
from cerebrum.infrastructure.llm.registry import build_llm_provider


def get_llm_provider(
    settings: SettingsDep,
    http_client: HttpClientDep,
    provider: Annotated[
        str | None,
        Query(description="Override the deployment's default LLM provider."),
    ] = None,
) -> LLMProvider:
    return build_llm_provider(
        provider or settings.ai.default_provider,
        settings=settings.ai,
        http_client=http_client,
    )


def get_prompt_builder_service(
    event_dispatcher: EventDispatcherDep,
) -> PromptBuilderService:
    return PromptBuilderService(event_dispatcher=event_dispatcher)


def get_ai_response_service(event_dispatcher: EventDispatcherDep) -> AIResponseService:
    return AIResponseService(event_dispatcher=event_dispatcher)


def get_ai_usage_stats_service(redis: RedisDep) -> AIUsageStatsService:
    return AIUsageStatsService(redis=redis)


def get_rag_service(
    session: DbSessionDep,
    qdrant_client: QdrantDep,
    opensearch_client: OpenSearchDep,
    neo4j_driver: Neo4jDep,
    redis: RedisDep,
    event_dispatcher: EventDispatcherDep,
) -> RAGService:
    return RAGService(
        retrieval_service=get_retrieval_service(
            session, qdrant_client, opensearch_client, neo4j_driver, event_dispatcher
        ),
        context_builder_service=get_context_builder_service(
            session, neo4j_driver, event_dispatcher
        ),
        citation_service=get_citation_service(session, event_dispatcher),
        prompt_builder_service=get_prompt_builder_service(event_dispatcher),
        response_service=get_ai_response_service(event_dispatcher),
        usage_stats_service=get_ai_usage_stats_service(redis),
        event_dispatcher=event_dispatcher,
    )


LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
PromptBuilderServiceDep = Annotated[
    PromptBuilderService, Depends(get_prompt_builder_service)
]
AIResponseServiceDep = Annotated[AIResponseService, Depends(get_ai_response_service)]
AIUsageStatsServiceDep = Annotated[
    AIUsageStatsService, Depends(get_ai_usage_stats_service)
]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
