"""``ConversationSummaryService``: CIS Phase 4 Prompt 2's Automatic
Conversation Summarization and Context Pruning — folds a conversation's
older messages into a running
:attr:`~cerebrum.infrastructure.database.models.conversation.Conversation.summary`
once it grows past a message-count threshold, advancing
:attr:`~cerebrum.infrastructure.database.models.conversation.Conversation.summarized_through_sequence`
so
:class:`~cerebrum.application.conversation.memory_service.MemoryService`
stops including those messages in its rolling window (they are already
represented, compressed, in ``summary``).

Reuses CIS Phase 4 Prompt 1's
:class:`~cerebrum.infrastructure.llm.provider.LLMProvider` abstraction
for the summarization call itself — the same provider a turn's answer
was generated with — rather than a separate summarization model/service
("Reuse the existing RAG engine... Do not duplicate functionality" per
this milestone's OBJECTIVE).
"""

import uuid

from cerebrum.application.conversation.events import ConversationSummarizedEvent
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.conversation import Conversation
from cerebrum.infrastructure.database.models.message import Message
from cerebrum.infrastructure.llm.provider import LLMMessage, LLMProvider
from cerebrum.repositories.postgres.conversation_repository import (
    ConversationRepository,
)
from cerebrum.repositories.postgres.message_repository import MessageRepository
from cerebrum.shared.errors.exceptions import NotFoundException

_DEFAULT_THRESHOLD_MESSAGES = 20
_DEFAULT_KEEP_RECENT_MESSAGES = 6
_SUMMARY_MAX_TOKENS = 400

_SUMMARIZER_SYSTEM_PROMPT = (
    "You summarize conversation excerpts concisely and factually, "
    "preserving key facts, decisions, and open questions. Do not add "
    "information that was not in the excerpt."
)


class ConversationSummaryService:
    def __init__(
        self,
        *,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._conversations = conversation_repository
        self._messages = message_repository
        self._events = event_dispatcher

    async def maybe_summarize(
        self,
        conversation_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        provider: LLMProvider,
        threshold: int = _DEFAULT_THRESHOLD_MESSAGES,
        keep_recent: int = _DEFAULT_KEEP_RECENT_MESSAGES,
    ) -> Conversation | None:
        """Summarizes and prunes only once ``threshold`` unsummarized
        messages have accumulated, leaving the most recent
        ``keep_recent`` out of the summary (still "fresh" for
        ``MemoryService``'s rolling window). Returns ``None`` (and does
        nothing) when the threshold has not been reached yet — most
        calls, since this is checked after every turn.
        """
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            raise NotFoundException(f"No conversation with id {conversation_id}.")

        unsummarized = await self._messages.list_by_conversation(
            conversation_id, after_sequence=conversation.summarized_through_sequence
        )
        if len(unsummarized) < threshold:
            return None

        to_summarize = unsummarized[:-keep_recent] if keep_recent > 0 else unsummarized
        if not to_summarize:
            return None

        conversation.summary = await self._summarize(
            conversation.summary, to_summarize, provider=provider
        )
        conversation.summarized_through_sequence = to_summarize[-1].sequence_index
        updated = await self._conversations.update(conversation)

        self._events.publish(
            ConversationSummarizedEvent(
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                summarized_through_sequence=conversation.summarized_through_sequence,
            )
        )
        return updated

    @staticmethod
    async def _summarize(
        existing_summary: str | None, messages: list[Message], *, provider: LLMProvider
    ) -> str:
        transcript = "\n".join(f"{m.role}: {m.content}" for m in messages)
        prior = (
            f"Existing summary so far: {existing_summary}\n\n"
            if existing_summary
            else ""
        )
        user_prompt = f"{prior}Summarize this conversation excerpt:\n\n{transcript}"
        response = await provider.generate(
            [
                LLMMessage(role="system", content=_SUMMARIZER_SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_prompt),
            ],
            temperature=0.0,
            max_tokens=_SUMMARY_MAX_TOKENS,
        )
        return response.content
