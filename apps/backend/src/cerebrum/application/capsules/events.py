"""CIS Phase 5 Prompt 3's Capsule Events — emission side only, mirroring
cerebrum.application.connectors.events/cerebrum.application.workflows.events's
identical precedent (nothing in this codebase subscribes to
domain-specific business events across module boundaries; the
"Continuous Updates" requirement instead subscribes to the *existing*
events other domains already emit — see
cerebrum.application.capsules.continuous_updates).
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class CapsuleCreatedEvent(DomainEvent):
    event_type: str = "capsule.created"
    capsule_id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class CapsuleLinkedEvent(DomainEvent):
    event_type: str = "capsule.linked"
    capsule_id: uuid.UUID
    workspace_id: uuid.UUID
    person_entity_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class CapsuleRefreshedEvent(DomainEvent):
    event_type: str = "capsule.refreshed"
    capsule_id: uuid.UUID
    workspace_id: uuid.UUID
    expertise_count: int
    ownership_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CapsuleMarkedStaleEvent(DomainEvent):
    event_type: str = "capsule.marked_stale"
    capsule_id: uuid.UUID
    workspace_id: uuid.UUID
    reason: str
