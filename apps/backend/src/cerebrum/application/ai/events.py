"""Concrete domain events CIS Phase 4 Prompt 1's RAG engine raises —
alongside cerebrum.application.retrieval.events's three events, these
extend the same cerebrum.events.dispatcher.EventDispatcher. Emission
side only — nothing in this codebase subscribes to any of these yet.
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptBuiltEvent(DomainEvent):
    event_type: str = "ai.prompt_built"
    workspace_id: uuid.UUID
    estimated_tokens: int
    truncated: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseStreamStartedEvent(DomainEvent):
    event_type: str = "ai.response_stream_started"
    workspace_id: uuid.UUID
    provider: str
    model: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AIResponseGeneratedEvent(DomainEvent):
    event_type: str = "ai.response_generated"
    workspace_id: uuid.UUID
    provider: str
    model: str
    citation_count: int
    overall_confidence: float


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseCompletedEvent(DomainEvent):
    event_type: str = "ai.response_completed"
    workspace_id: uuid.UUID
    prompt_tokens: int
    completion_tokens: int
    streamed: bool
