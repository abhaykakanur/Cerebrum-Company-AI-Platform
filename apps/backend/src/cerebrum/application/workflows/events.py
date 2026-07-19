"""CIS Phase 5 Prompt 2's Workflow Events — emission side only, exactly
mirroring cerebrum.application.connectors.events's precedent (and its
docstring's caveat: nothing in this codebase subscribes to any of these
yet).
"""

import uuid
from dataclasses import dataclass

from cerebrum.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowCreatedEvent(DomainEvent):
    event_type: str = "workflow.created"
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowStartedEvent(DomainEvent):
    event_type: str = "workflow.started"
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID
    trigger_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StepStartedEvent(DomainEvent):
    event_type: str = "workflow.step_started"
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID
    step_id: str
    step_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StepCompletedEvent(DomainEvent):
    event_type: str = "workflow.step_completed"
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID
    step_id: str
    step_type: str
    status: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowCompletedEvent(DomainEvent):
    event_type: str = "workflow.completed"
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowFailedEvent(DomainEvent):
    event_type: str = "workflow.failed"
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    run_id: uuid.UUID
    error_message: str
