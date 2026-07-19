"""Request/response schemas for CIS Phase 5 Prompt 2's Workflow API.
Every response model inherits :class:`~cerebrum.api.schemas.base.APIModel`
— see cerebrum.api.schemas.connector's identical docstring precedent.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel
from cerebrum.infrastructure.database.models.workflow_schedule import ScheduleType
from cerebrum.infrastructure.database.models.workflow_version import TriggerType

# --- Requests ---------------------------------------------------------------


class CreateWorkflowRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    trigger_type: TriggerType
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]]
    workflow_metadata: dict[str, Any] = Field(default_factory=dict)
    is_template: bool = False


class UpdateWorkflowRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    trigger_type: TriggerType | None = None
    trigger_config: dict[str, Any] | None = None
    steps: list[dict[str, Any]] | None = None
    workflow_metadata: dict[str, Any] | None = None


class ExecuteWorkflowRequest(APIModel):
    trigger_context: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)


class CreateFromTemplateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)


class CreateScheduleRequest(APIModel):
    schedule_type: ScheduleType
    cron_expression: str | None = None
    run_at: datetime | None = None


# --- Responses ----------------------------------------------------------


class WorkflowResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    status: str
    is_template: bool
    current_version_id: uuid.UUID | None
    workflow_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkflowVersionResponse(APIModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    version_number: int
    trigger_type: str
    trigger_config: dict[str, Any]
    steps: list[dict[str, Any]]
    created_at: datetime


class WorkflowRunResponse(APIModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_version_id: uuid.UUID
    status: str
    trigger_type: str
    trigger_context: dict[str, Any]
    variables: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class WorkflowStepRunResponse(APIModel):
    id: uuid.UUID
    workflow_run_id: uuid.UUID
    step_id: str
    step_type: str
    status: str
    attempt: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    output: dict[str, Any]
    error_message: str | None


class WorkflowScheduleResponse(APIModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    schedule_type: str
    cron_expression: str | None
    run_at: datetime | None
    status: str
    next_run_at: datetime | None
    last_run_at: datetime | None
