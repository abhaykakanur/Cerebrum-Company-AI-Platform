"""Concrete domain events CIS Phase 3 Prompt 3's Retrieval Engine raises
— alongside cerebrum.application.semantic.events's three events and
cerebrum.application.knowledge_graph.events's three events, these extend
the same cerebrum.events.dispatcher.EventDispatcher. Emission side only
— nothing in this codebase subscribes to any of these yet.
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class RetrievalCompletedEvent(DomainEvent):
    event_type: str = "retrieval.completed"
    workspace_id: uuid.UUID
    strategy: str
    query_text: str | None
    result_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextBuiltEvent(DomainEvent):
    event_type: str = "retrieval.context_built"
    workspace_id: uuid.UUID
    document_count: int
    chunk_count: int
    entity_count: int
    truncated: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CitationGeneratedEvent(DomainEvent):
    event_type: str = "retrieval.citation_generated"
    workspace_id: uuid.UUID
    citation_count: int
