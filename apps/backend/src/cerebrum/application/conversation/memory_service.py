"""``MemoryService``: CIS Phase 4 Prompt 2's Conversation Memory —
builds a :class:`ConversationMemory` from a conversation's persisted
:class:`~cerebrum.infrastructure.database.models.message.Message` rows,
ready to hand to
:meth:`~cerebrum.application.ai.rag_service.RAGService.ask`/``ask_stream``'s
new ``conversation_history`` parameter (see that service's docstring
for how CIS Phase 4 Prompt 1's RAG Engine is reused, not duplicated,
for the actual generation step).

- **Short-term memory / Rolling context window**: the most recent
  messages, bounded by both a message count and a character budget
  (the same rough chars-per-token heuristic
  cerebrum.application.ai.prompt_builder_service already documents and
  uses) — :meth:`build`.
- **Context Pruning**: messages at or before
  :attr:`~cerebrum.infrastructure.database.models.conversation.Conversation.summarized_through_sequence`
  are excluded from the rolling window entirely — they are already
  folded into ``Conversation.summary`` (see
  cerebrum.application.conversation.conversation_summary_service.ConversationSummaryService),
  so including both would double-count them in the prompt.
- **Retrieval-aware memory**: every prior assistant message's
  ``context_references`` (the full retrieval-result reference set, not
  just what was cited) are collected into
  :attr:`ConversationMemory.previously_referenced_document_ids`/``entity_ids``
  — exposed for a caller that wants to bias a follow-up retrieval
  toward what this conversation already established, though this
  milestone's :class:`~cerebrum.application.conversation.session_service.SessionService`
  does not yet act on them beyond surfacing them (see that service's
  docstring).
- **Citation preservation**: every prior assistant message's
  ``citations`` are collected into
  :attr:`ConversationMemory.carried_citations` unchanged (not
  re-verified, not re-scored) — a follow-up answer can still reference
  "the report cited two turns ago" because that citation's full record
  survives in memory, not just the message text that mentioned it.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from cerebrum.infrastructure.database.models.message import Message, MessageRole
from cerebrum.infrastructure.llm.provider import LLMMessage, Role
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository
from cerebrum.shared.errors.exceptions import NotFoundException

_CHARS_PER_TOKEN = 4
_DEFAULT_MAX_MESSAGES = 10
_DEFAULT_MAX_TOKENS = 2000

_ROLE_TO_LLM_ROLE: dict[str, Role] = {
    MessageRole.USER.value: "user",
    MessageRole.ASSISTANT.value: "assistant",
    MessageRole.SYSTEM.value: "system",
}


@dataclass(frozen=True, slots=True)
class ConversationMemory:
    conversation_id: uuid.UUID
    summary: str | None
    recent_messages: list[Message]
    carried_citations: list[dict[str, Any]] = field(default_factory=list)
    previously_referenced_document_ids: set[str] = field(default_factory=set)
    previously_referenced_entity_ids: set[str] = field(default_factory=set)
    truncated: bool = False

    def as_llm_messages(self) -> list[LLMMessage]:
        """Renders this memory as prior turns for
        cerebrum.application.ai.prompt_builder_service.PromptBuilderService's
        ``conversation_history`` parameter — the conversation summary
        (if any) first, as a synthetic system-role note, then each
        recent message in its original role.
        """
        messages: list[LLMMessage] = []
        if self.summary:
            messages.append(
                LLMMessage(
                    role="system",
                    content=f"Summary of earlier conversation: {self.summary}",
                )
            )
        for message in self.recent_messages:
            messages.append(
                LLMMessage(
                    role=_ROLE_TO_LLM_ROLE.get(message.role, "user"),
                    content=message.content,
                )
            )
        return messages


class MemoryService:
    def __init__(
        self,
        *,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ) -> None:
        self._conversations = conversation_repository
        self._messages = message_repository

    async def build_memory(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        max_messages: int = _DEFAULT_MAX_MESSAGES,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> ConversationMemory:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise NotFoundException(f"No conversation with id {conversation_id}.")

        unsummarized = await self._messages.list_by_conversation(
            conversation_id, after_sequence=conversation.summarized_through_sequence
        )

        recent, truncated = _apply_rolling_window(
            unsummarized, max_messages=max_messages, max_tokens=max_tokens
        )

        carried_citations: list[dict[str, Any]] = []
        document_ids: set[str] = set()
        entity_ids: set[str] = set()
        for message in unsummarized:
            if message.role != MessageRole.ASSISTANT.value:
                continue
            carried_citations.extend(message.citations)
            for reference in message.context_references:
                document_id = reference.get("document_id")
                entity_id = reference.get("entity_id")
                if document_id:
                    document_ids.add(str(document_id))
                if entity_id:
                    entity_ids.add(str(entity_id))

        return ConversationMemory(
            conversation_id=conversation_id,
            summary=conversation.summary,
            recent_messages=recent,
            carried_citations=carried_citations,
            previously_referenced_document_ids=document_ids,
            previously_referenced_entity_ids=entity_ids,
            truncated=truncated,
        )


def _apply_rolling_window(
    messages: list[Message], *, max_messages: int, max_tokens: int
) -> tuple[list[Message], bool]:
    tail = messages[-max_messages:]
    truncated = len(tail) < len(messages)

    budget = max_tokens * _CHARS_PER_TOKEN
    kept: list[Message] = []
    for message in reversed(tail):
        cost = len(message.content)
        if kept and cost > budget:
            truncated = True
            break
        budget -= cost
        kept.append(message)
    kept.reverse()
    return kept, truncated
