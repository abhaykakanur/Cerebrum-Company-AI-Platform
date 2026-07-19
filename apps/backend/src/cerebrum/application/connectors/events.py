"""Concrete domain events CIS Phase 5 Prompt 1's Connector Framework
raises — alongside every other phase's events, these extend the same
cerebrum.events.dispatcher.EventDispatcher. Emission side only —
nothing in this codebase subscribes to any of these yet.
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ConnectorRegisteredEvent(DomainEvent):
    event_type: str = "connector.registered"
    connector_id: uuid.UUID
    workspace_id: uuid.UUID
    connector_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncStartedEvent(DomainEvent):
    event_type: str = "connector.sync_started"
    connector_id: uuid.UUID
    workspace_id: uuid.UUID
    sync_run_id: uuid.UUID
    sync_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncCompletedEvent(DomainEvent):
    event_type: str = "connector.sync_completed"
    connector_id: uuid.UUID
    workspace_id: uuid.UUID
    sync_run_id: uuid.UUID
    items_processed: int
    items_skipped: int
    items_failed: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncFailedEvent(DomainEvent):
    event_type: str = "connector.sync_failed"
    connector_id: uuid.UUID
    workspace_id: uuid.UUID
    sync_run_id: uuid.UUID
    error_message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ConnectorHealthyEvent(DomainEvent):
    event_type: str = "connector.healthy"
    connector_id: uuid.UUID
    workspace_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ConnectorUnhealthyEvent(DomainEvent):
    event_type: str = "connector.unhealthy"
    connector_id: uuid.UUID
    workspace_id: uuid.UUID
    message: str
