"""``SessionService``: CIS Phase 4 Prompt 2's Session Management — the
single orchestrator for a full conversational turn: load/build memory
(:class:`~cerebrum.application.conversation.memory_service.MemoryService`),
invoke CIS Phase 4 Prompt 1's
:class:`~cerebrum.application.ai.rag_service.RAGService` with that
memory as conversation history, persist both the user and assistant
:class:`~cerebrum.infrastructure.database.models.message.Message` rows
via
:class:`~cerebrum.application.conversation.conversation_service.ConversationService`,
and trigger
:class:`~cerebrum.application.conversation.conversation_summary_service.ConversationSummaryService`'s
threshold check — never re-implementing retrieval, prompting, or
generation itself (this milestone's OBJECTIVE: "Reuse the existing RAG
engine... Do not duplicate functionality").

Distinct from ``ConversationService``: that service owns persistence
primitives (CRUD, history, search) any caller can use directly (e.g.
the read-only ``GET /conversations`` routes); this service owns the
*live* turn — "session" in CIS Phase 4 Prompt 2's sense is the active
back-and-forth, not a separate stored entity (there is no ``Session``
table — see cerebrum.infrastructure.database.models.conversation's
docstring on why ``session_id`` is a plain correlation field, not a
foreign key).

Retrieval-aware memory (CIS Phase 4 Prompt 2) surfaces via
:attr:`~cerebrum.application.conversation.memory_service.ConversationMemory.previously_referenced_document_ids`/``entity_ids``,
computed by ``MemoryService`` and available to a caller that wants it
(e.g. :meth:`resume`'s return value) — this milestone's turn flow does
not yet feed them back into retrieval as a bias/filter (that would be
query-planning logic belonging to
cerebrum.application.retrieval.retrieval_service.RetrievalService, out
of this prompt's scope), only surfaces them.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from cerebrum.application.ai.ai_response_service import RAGAnswer
from cerebrum.application.ai.rag_service import CompletedEvent, RAGService, StreamEvent
from cerebrum.application.conversation.conversation_service import ConversationService
from cerebrum.application.conversation.conversation_summary_service import (
    ConversationSummaryService,
)
from cerebrum.application.conversation.memory_service import (
    ConversationMemory,
    MemoryService,
)
from cerebrum.application.retrieval.citation_service import EnrichedCitation
from cerebrum.application.retrieval.retrieval_service import RetrievalStrategy
from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message, MessageRole
from cerebrum.infrastructure.llm.provider import LLMProvider


@dataclass(frozen=True, slots=True)
class TurnResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    answer: RAGAnswer


class SessionService:
    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        memory_service: MemoryService,
        summary_service: ConversationSummaryService,
        rag_service: RAGService,
    ) -> None:
        self._conversations = conversation_service
        self._memory = memory_service
        self._summaries = summary_service
        self._rag = rag_service

    async def create_session(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        session_id: str | None = None,
    ) -> Conversation:
        return await self._conversations.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            title=title,
            session_id=session_id,
        )

    async def resume(
        self, conversation_id: uuid.UUID, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Conversation, list[Message], ConversationMemory]:
        """Resume Conversation — CIS Phase 4 Prompt 2's Session
        Management requirement: the conversation itself, its full
        message history (for display), and the memory a follow-up
        :meth:`send_message` call would actually use.
        """
        conversation = await self._conversations.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        history = await self._conversations.get_history(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        memory = await self._memory.build_memory(
            conversation_id, workspace_id=workspace_id
        )
        return conversation, history, memory

    async def send_message(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        provider: LLMProvider,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        model: str | None = None,
        limit: int = 10,
        max_context_tokens: int = 3000,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> TurnResult:
        conversation = await self._conversations.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        memory = await self._memory.build_memory(
            conversation_id, workspace_id=workspace_id
        )

        user_message = await self._conversations.add_message(
            conversation_id,
            workspace_id=workspace_id,
            role=MessageRole.USER,
            content=question,
        )

        answer = await self._rag.ask(
            question,
            workspace_id=workspace_id,
            provider=provider,
            strategy=strategy,
            model=model,
            limit=limit,
            max_context_tokens=max_context_tokens,
            max_tokens=max_tokens,
            temperature=temperature,
            conversation_history=memory.as_llm_messages(),
        )

        assistant_message = await self._conversations.add_message(
            conversation_id,
            workspace_id=workspace_id,
            role=MessageRole.ASSISTANT,
            content=answer.answer,
            citations=[_citation_to_dict(c) for c in answer.citations],
            context_references=[
                _citation_to_dict(c) for c in answer.all_retrieved_citations
            ],
            confidence=answer.confidence.overall,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
        )

        await self._summaries.maybe_summarize(
            conversation_id, workspace_id=workspace_id, provider=provider
        )

        return TurnResult(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            answer=answer,
        )

    async def send_message_stream(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        provider: LLMProvider,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        model: str | None = None,
        limit: int = 10,
        max_context_tokens: int = 3000,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        cancellation: asyncio.Event | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream Message — the same progress/token/completed events
        :meth:`~cerebrum.application.ai.rag_service.RAGService.ask_stream`
        already yields (CIS Phase 4 Prompt 2's Streaming responses,
        Streaming citations, Cancellation, and Progress updates are all
        inherited from it unchanged), plus persistence: the user
        message is written immediately (before generation starts, so it
        survives even a cancelled/failed stream), and the assistant
        message is written only once
        :class:`~cerebrum.application.ai.rag_service.CompletedEvent`
        arrives — a cancelled or errored stream leaves no partial
        assistant message behind.
        """
        await self._conversations.get(
            conversation_id, workspace_id=workspace_id, user_id=user_id
        )
        memory = await self._memory.build_memory(
            conversation_id, workspace_id=workspace_id
        )
        await self._conversations.add_message(
            conversation_id,
            workspace_id=workspace_id,
            role=MessageRole.USER,
            content=question,
        )

        async for event in self._rag.ask_stream(
            question,
            workspace_id=workspace_id,
            provider=provider,
            strategy=strategy,
            model=model,
            limit=limit,
            max_context_tokens=max_context_tokens,
            max_tokens=max_tokens,
            temperature=temperature,
            conversation_history=memory.as_llm_messages(),
            cancellation=cancellation,
        ):
            if isinstance(event, CompletedEvent):
                answer = event.answer
                await self._conversations.add_message(
                    conversation_id,
                    workspace_id=workspace_id,
                    role=MessageRole.ASSISTANT,
                    content=answer.answer,
                    citations=[_citation_to_dict(c) for c in answer.citations],
                    context_references=[
                        _citation_to_dict(c) for c in answer.all_retrieved_citations
                    ],
                    confidence=answer.confidence.overall,
                    prompt_tokens=answer.prompt_tokens,
                    completion_tokens=answer.completion_tokens,
                )
                await self._summaries.maybe_summarize(
                    conversation_id, workspace_id=workspace_id, provider=provider
                )
            yield event


def _citation_to_dict(citation: EnrichedCitation) -> dict[str, Any]:
    return {
        "document_id": str(citation.document_id) if citation.document_id else None,
        "document_version_id": (
            str(citation.document_version_id) if citation.document_version_id else None
        ),
        "chunk_id": str(citation.chunk_id) if citation.chunk_id else None,
        "entity_id": str(citation.entity_id) if citation.entity_id else None,
        "confidence": citation.confidence,
        "document_name": citation.document_name,
        "version_number": citation.version_number,
        "chunk_index": citation.chunk_index,
        "entity_name": citation.entity_name,
    }
