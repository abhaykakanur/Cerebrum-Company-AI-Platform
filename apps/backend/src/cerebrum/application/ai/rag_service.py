"""``RAGService``: CIS Phase 4 Prompt 1's Enterprise RAG Engine — the
one orchestrator tying together Retrieval Orchestration (delegates to
:class:`~cerebrum.application.retrieval.retrieval_service.RetrievalService`,
never reimplementing retrieval), Context Assembly
(:class:`~cerebrum.application.retrieval.context_builder_service.ContextBuilderService`),
Prompt Generation
(:class:`~cerebrum.application.ai.prompt_builder_service.PromptBuilderService`),
LLM Invocation
(:class:`~cerebrum.infrastructure.llm.provider.LLMProvider`, injected
per call — provider selection is the caller's/DI layer's concern, never
this service's), Response Generation and Citation Attachment
(:class:`~cerebrum.application.ai.ai_response_service.AIResponseService`).

:meth:`ask` is the non-streaming path; :meth:`ask_stream` is the
Streaming requirement — an async generator of :data:`StreamEvent`
(progress stages, individual tokens, cancellation, error, or the final
answer), consumed directly by the SSE API route
(cerebrum.api.v1.ai.stream_answer). Passing a ``cancellation``
``asyncio.Event`` and setting it mid-stream stops pulling further
tokens from the provider (closing its underlying async generator) and
yields :class:`CancelledEvent` instead of :class:`CompletedEvent` — CIS
Phase 4 Prompt 1's Cancellation requirement.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from cerebrum.application.ai.ai_response_service import AIResponseService, RAGAnswer
from cerebrum.application.ai.events import (
    ResponseCompletedEvent,
    ResponseStreamStartedEvent,
)
from cerebrum.application.ai.prompt_builder_service import PromptBuilderService
from cerebrum.application.ai.usage_stats_service import AIUsageStatsService
from cerebrum.application.retrieval.citation_service import CitationService
from cerebrum.application.retrieval.context_builder_service import (
    ContextBuilderService,
)
from cerebrum.application.retrieval.retrieval_service import (
    RetrievalService,
    RetrievalStrategy,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMUsage,
)
from cerebrum.shared.errors.exceptions import InfrastructureException


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    stage: str
    type: str = "progress"


@dataclass(frozen=True, slots=True)
class TokenEvent:
    token: str
    type: str = "token"


@dataclass(frozen=True, slots=True)
class CompletedEvent:
    answer: RAGAnswer
    type: str = "completed"


@dataclass(frozen=True, slots=True)
class CancelledEvent:
    type: str = "cancelled"


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    message: str
    type: str = "error"


StreamEvent = ProgressEvent | TokenEvent | CompletedEvent | CancelledEvent | ErrorEvent


class RAGService:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        context_builder_service: ContextBuilderService,
        citation_service: CitationService,
        prompt_builder_service: PromptBuilderService,
        response_service: AIResponseService,
        usage_stats_service: AIUsageStatsService,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._retrieval = retrieval_service
        self._context_builder = context_builder_service
        self._citations = citation_service
        self._prompt_builder = prompt_builder_service
        self._response = response_service
        self._usage = usage_stats_service
        self._events = event_dispatcher

    async def ask(
        self,
        question: str,
        *,
        workspace_id: uuid.UUID,
        provider: LLMProvider,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        model: str | None = None,
        limit: int = 10,
        max_context_tokens: int = 3000,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        conversation_history: list[LLMMessage] | None = None,
    ) -> RAGAnswer:
        retrieval_result = await self._retrieval.retrieve(
            question, workspace_id=workspace_id, strategy=strategy, limit=limit
        )
        context = await self._context_builder.build(
            retrieval_result.hits,
            workspace_id=workspace_id,
            query_text=question,
            max_chunks=limit,
            max_entities=limit,
        )
        citations = await self._citations.build_citations(
            retrieval_result.hits, workspace_id=workspace_id
        )
        prompt = self._prompt_builder.build(
            question=question,
            context=context,
            citations=citations,
            workspace_id=workspace_id,
            max_context_tokens=max_context_tokens,
            conversation_history=conversation_history,
        )

        try:
            llm_response = await provider.generate(
                [prompt.system_message, prompt.user_message],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMProviderError as exc:
            raise InfrastructureException(str(exc), cause=exc) from exc

        answer = self._response.build_answer(
            llm_response=llm_response,
            prompt=prompt,
            retrieval_result=retrieval_result,
            context=context,
            requested_limit=limit,
            workspace_id=workspace_id,
        )
        await self._usage.record(
            workspace_id=workspace_id,
            provider=llm_response.provider,
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
        )
        self._events.publish(
            ResponseCompletedEvent(
                workspace_id=workspace_id,
                prompt_tokens=llm_response.usage.prompt_tokens,
                completion_tokens=llm_response.usage.completion_tokens,
                streamed=False,
            )
        )
        return answer

    async def ask_stream(
        self,
        question: str,
        *,
        workspace_id: uuid.UUID,
        provider: LLMProvider,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        model: str | None = None,
        limit: int = 10,
        max_context_tokens: int = 3000,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        conversation_history: list[LLMMessage] | None = None,
        cancellation: asyncio.Event | None = None,
    ) -> AsyncIterator[StreamEvent]:
        yield ProgressEvent(stage="retrieving")
        retrieval_result = await self._retrieval.retrieve(
            question, workspace_id=workspace_id, strategy=strategy, limit=limit
        )
        if cancellation is not None and cancellation.is_set():
            yield CancelledEvent()
            return

        yield ProgressEvent(stage="building_context")
        context = await self._context_builder.build(
            retrieval_result.hits,
            workspace_id=workspace_id,
            query_text=question,
            max_chunks=limit,
            max_entities=limit,
        )
        citations = await self._citations.build_citations(
            retrieval_result.hits, workspace_id=workspace_id
        )
        if cancellation is not None and cancellation.is_set():
            yield CancelledEvent()
            return

        yield ProgressEvent(stage="building_prompt")
        prompt = self._prompt_builder.build(
            question=question,
            context=context,
            citations=citations,
            workspace_id=workspace_id,
            max_context_tokens=max_context_tokens,
            conversation_history=conversation_history,
        )

        resolved_model = model or provider.default_model
        self._events.publish(
            ResponseStreamStartedEvent(
                workspace_id=workspace_id, provider=provider.name, model=resolved_model
            )
        )
        yield ProgressEvent(stage="generating")

        chunks: list[str] = []
        token_stream = provider.stream(
            [prompt.system_message, prompt.user_message],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            async for token in token_stream:
                if cancellation is not None and cancellation.is_set():
                    await token_stream.aclose()
                    yield CancelledEvent()
                    return
                chunks.append(token)
                yield TokenEvent(token=token)
        except LLMProviderError as exc:
            yield ErrorEvent(message=str(exc))
            return

        content = "".join(chunks)
        llm_response = LLMResponse(
            content=content,
            model=resolved_model,
            provider=provider.name,
            usage=LLMUsage(
                prompt_tokens=prompt.estimated_tokens,
                completion_tokens=max(len(content) // 4, 1),
            ),
        )
        answer = self._response.build_answer(
            llm_response=llm_response,
            prompt=prompt,
            retrieval_result=retrieval_result,
            context=context,
            requested_limit=limit,
            workspace_id=workspace_id,
        )
        await self._usage.record(
            workspace_id=workspace_id,
            provider=llm_response.provider,
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
        )
        self._events.publish(
            ResponseCompletedEvent(
                workspace_id=workspace_id,
                prompt_tokens=llm_response.usage.prompt_tokens,
                completion_tokens=llm_response.usage.completion_tokens,
                streamed=True,
            )
        )
        yield CompletedEvent(answer=answer)
