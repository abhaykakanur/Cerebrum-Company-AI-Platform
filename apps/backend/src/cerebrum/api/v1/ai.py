"""The Enterprise RAG Engine API surface — CIS Phase 4 Prompt 1's Ask
Question, Stream Response, Retrieve Citations, AI Configuration, and
Conversation Statistics endpoints, built entirely on
:class:`~cerebrum.application.ai.rag_service.RAGService` and the CIS
Phase 3 retrieval services it composes (see
cerebrum.application.ai's package docstring). Asking/streaming use the
``"ai:ask"`` permission code (a resource-consuming action, distinct
from read-only queries); citations/config/statistics use ``"ai:read"``,
mirroring cerebrum.api.v1.retrieval's read/write permission split.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import build_success_response
from cerebrum.api.schemas.ai import (
    AIProviderConfigResponse,
    AIUsageStatisticsResponse,
    AskRequest,
    CitationsRequest,
    RAGAnswerResponse,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.retrieval import EnrichedCitationResponse
from cerebrum.application.ai.rag_service import (
    CancelledEvent,
    CompletedEvent,
    ErrorEvent,
    ProgressEvent,
    StreamEvent,
    TokenEvent,
)
from cerebrum.dependencies.ai import (
    AIUsageStatsServiceDep,
    LLMProviderDep,
    RAGServiceDep,
)
from cerebrum.dependencies.auth import WorkspaceIdDep, require_permission
from cerebrum.dependencies.retrieval import CitationServiceDep, RetrievalServiceDep
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.infrastructure.llm.registry import available_providers

router = APIRouter(prefix="/ai", tags=["AI"], responses=STANDARD_ERROR_RESPONSES)

_ask = Depends(require_permission("ai:ask"))
_read = Depends(require_permission("ai:read"))

_DISCONNECT_POLL_SECONDS = 0.5


@router.post(
    "/ask",
    response_model=SuccessResponse[RAGAnswerResponse],
    dependencies=[_ask],
)
async def ask_question(
    body: AskRequest,
    workspace_id: WorkspaceIdDep,
    rag: RAGServiceDep,
    provider: LLMProviderDep,
    settings: SettingsDep,
) -> SuccessResponse[RAGAnswerResponse]:
    """Ask Question — CIS Phase 4 Prompt 1's core RAG endpoint: runs
    retrieval, builds context and a citation-backed prompt, invokes the
    selected (or default) provider, and returns one complete answer.
    """
    answer = await rag.ask(
        body.question,
        workspace_id=workspace_id,
        provider=provider,
        strategy=body.strategy,
        model=body.model,
        limit=body.limit,
        max_context_tokens=body.max_context_tokens,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )
    return build_success_response(
        RAGAnswerResponse.from_answer(answer), settings=settings
    )


@router.post("/ask/stream", dependencies=[_ask])
async def stream_answer(
    request: Request,
    body: AskRequest,
    workspace_id: WorkspaceIdDep,
    rag: RAGServiceDep,
    provider: LLMProviderDep,
) -> StreamingResponse:
    """Stream Response — CIS Phase 4 Prompt 1's Streaming requirement:
    Server-Sent Events, one ``data:`` line per progress stage/token/
    completion. Cancellation: a background watcher sets the
    ``asyncio.Event`` :meth:`~cerebrum.application.ai.rag_service.RAGService.ask_stream`
    checks between tokens as soon as the client disconnects — no
    further provider tokens are requested after that point.
    """
    cancellation = asyncio.Event()

    async def _watch_for_disconnect() -> None:
        while not cancellation.is_set():
            if await request.is_disconnected():
                cancellation.set()
                return
            await asyncio.sleep(_DISCONNECT_POLL_SECONDS)

    async def _body() -> AsyncIterator[bytes]:
        watcher = asyncio.create_task(_watch_for_disconnect())
        try:
            async for event in rag.ask_stream(
                body.question,
                workspace_id=workspace_id,
                provider=provider,
                strategy=body.strategy,
                model=body.model,
                limit=body.limit,
                max_context_tokens=body.max_context_tokens,
                max_tokens=body.max_tokens,
                temperature=body.temperature,
                cancellation=cancellation,
            ):
                yield _encode_sse(event)
        finally:
            cancellation.set()
            watcher.cancel()

    return StreamingResponse(_body(), media_type="text/event-stream")


@router.post(
    "/citations",
    response_model=SuccessResponse[list[EnrichedCitationResponse]],
    dependencies=[_read],
)
async def retrieve_citations(
    body: CitationsRequest,
    workspace_id: WorkspaceIdDep,
    retrieval: RetrievalServiceDep,
    citation_service: CitationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[list[EnrichedCitationResponse]]:
    """Retrieve Citations — runs retrieval and citation-building alone,
    without invoking any LLM provider; a cheap preview of what an
    ``/ai/ask`` call against the same question would cite.
    """
    result = await retrieval.retrieve(
        body.question,
        workspace_id=workspace_id,
        strategy=body.strategy,
        limit=body.limit,
    )
    citations = await citation_service.build_citations(
        result.hits, workspace_id=workspace_id
    )
    return build_success_response(
        [EnrichedCitationResponse.from_citation(c) for c in citations],
        settings=settings,
    )


@router.get(
    "/config",
    response_model=SuccessResponse[AIProviderConfigResponse],
    dependencies=[_read],
)
async def get_ai_configuration(
    settings: SettingsDep,
) -> SuccessResponse[AIProviderConfigResponse]:
    """AI Configuration — which providers this deployment has
    configured, the default provider/generation parameters, and each
    provider's default model. Never exposes an API key.
    """
    ai_settings = settings.ai
    return build_success_response(
        AIProviderConfigResponse(
            available_providers=available_providers(ai_settings),
            default_provider=ai_settings.default_provider,
            default_temperature=ai_settings.default_temperature,
            default_max_tokens=ai_settings.default_max_tokens,
            default_max_context_tokens=ai_settings.default_max_context_tokens,
            default_model_by_provider={
                "openai": ai_settings.openai_default_model,
                "anthropic": ai_settings.anthropic_default_model,
                "gemini": ai_settings.gemini_default_model,
                "ollama": ai_settings.ollama_default_model,
                "local": ai_settings.local_default_model,
            },
        ),
        settings=settings,
    )


@router.get(
    "/statistics",
    response_model=SuccessResponse[AIUsageStatisticsResponse],
    dependencies=[_read],
)
async def get_ai_statistics(
    workspace_id: WorkspaceIdDep,
    usage_stats: AIUsageStatsServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[AIUsageStatisticsResponse]:
    """Conversation Statistics — aggregate question/token counters for
    this workspace (never conversation content — see
    cerebrum.application.ai.usage_stats_service.AIUsageStatsService's
    docstring).
    """
    stats = await usage_stats.get_statistics(workspace_id=workspace_id)
    return build_success_response(
        AIUsageStatisticsResponse.from_stats(stats), settings=settings
    )


def _encode_sse(event: StreamEvent) -> bytes:
    return f"data: {json.dumps(_serialize_stream_event(event))}\n\n".encode()


def _serialize_stream_event(event: StreamEvent) -> dict[str, Any]:
    if isinstance(event, ProgressEvent):
        return {"type": "progress", "stage": event.stage}
    if isinstance(event, TokenEvent):
        return {"type": "token", "token": event.token}
    if isinstance(event, CompletedEvent):
        return {
            "type": "completed",
            "answer": RAGAnswerResponse.from_answer(event.answer).model_dump(
                mode="json"
            ),
        }
    if isinstance(event, CancelledEvent):
        return {"type": "cancelled"}
    if isinstance(event, ErrorEvent):
        return {"type": "error", "message": event.message}
    raise AssertionError(f"Unhandled stream event: {event!r}")
