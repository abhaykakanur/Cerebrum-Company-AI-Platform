"""Concrete domain events CIS Phase 3 Prompt 2's Semantic Intelligence
layer raises — alongside
cerebrum.application.knowledge.events.DocumentKnowledgePreparedEvent
and cerebrum.application.knowledge_graph.events's three events, these
extend the same cerebrum.events.dispatcher.EventDispatcher. Emission
side only — nothing in this codebase subscribes to any of these yet.
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class EmbeddingsGeneratedEvent(DomainEvent):
    event_type: str = "semantic.embeddings_generated"
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    embedding_count: int
    embedding_model: str


@dataclass(frozen=True, slots=True, kw_only=True)
class VectorIndexUpdatedEvent(DomainEvent):
    event_type: str = "semantic.vector_index_updated"
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    vector_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchIndexUpdatedEvent(DomainEvent):
    event_type: str = "semantic.search_index_updated"
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    indexed_count: int
