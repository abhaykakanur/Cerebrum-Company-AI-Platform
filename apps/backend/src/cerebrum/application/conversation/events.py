"""Concrete domain events CIS Phase 4 Prompt 2's Conversation
Management raises — alongside cerebrum.application.ai.events's four
events and cerebrum.application.retrieval.events's three events, these
extend the same cerebrum.events.dispatcher.EventDispatcher. Emission
side only — nothing in this codebase subscribes to any of these yet.
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ConversationCreatedEvent(DomainEvent):
    event_type: str = "conversation.created"
    conversation_id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class MessageAddedEvent(DomainEvent):
    event_type: str = "conversation.message_added"
    conversation_id: uuid.UUID
    workspace_id: uuid.UUID
    message_id: uuid.UUID
    role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ConversationSummarizedEvent(DomainEvent):
    event_type: str = "conversation.summarized"
    conversation_id: uuid.UUID
    workspace_id: uuid.UUID
    summarized_through_sequence: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ConversationArchivedEvent(DomainEvent):
    event_type: str = "conversation.archived"
    conversation_id: uuid.UUID
    workspace_id: uuid.UUID
