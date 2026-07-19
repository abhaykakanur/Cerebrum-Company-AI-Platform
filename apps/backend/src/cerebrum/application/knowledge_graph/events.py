"""Concrete domain events CIS Phase 3 Prompt 1's Knowledge Graph
raises — alongside
cerebrum.application.knowledge.events.DocumentKnowledgePreparedEvent,
these are the second real user of the previously-framework-only
cerebrum.events.dispatcher.EventDispatcher. Emission side only —
nothing in this codebase subscribes to any of these yet.
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityExtractedEvent(DomainEvent):
    event_type: str = "knowledge_graph.entity_extracted"
    entity_id: uuid.UUID
    workspace_id: uuid.UUID
    entity_type: str
    was_created: bool
    """``False`` means the extraction matched an existing entity (see
    cerebrum.application.knowledge_graph.entity_service.EntityService.upsert_from_extraction)
    and was merged into it rather than creating a new row.
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipExtractedEvent(DomainEvent):
    event_type: str = "knowledge_graph.relationship_extracted"
    relationship_id: uuid.UUID
    workspace_id: uuid.UUID
    relationship_type: str
    was_created: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphUpdatedEvent(DomainEvent):
    event_type: str = "knowledge_graph.graph_updated"
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    entity_count: int
    relationship_count: int
