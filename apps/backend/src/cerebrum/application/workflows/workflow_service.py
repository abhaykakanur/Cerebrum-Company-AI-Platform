"""``WorkflowService``: CIS Phase 5 Prompt 2's Workflow Definition,
Workflow Versioning, Workflow Validation, and Workflow Templates.
Mirrors
cerebrum.application.connectors.connector_service.ConnectorService's
register/get/configure/delete/list shape, composed with
cerebrum.application.knowledge.version_service.VersionService's
"every definition change creates a new immutable version" pattern:
:meth:`update_definition` never mutates an existing
:class:`~cerebrum.infrastructure.database.models.workflow_version.WorkflowVersion`,
it always creates the next one and repoints
:attr:`~cerebrum.infrastructure.database.models.workflow.Workflow.current_version_id`.
"""

import uuid
from typing import Any

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.events import WorkflowCreatedEvent
from cerebrum.application.workflows.validation import validate_steps, validate_trigger
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.workflow import Workflow, WorkflowStatus
from cerebrum.infrastructure.database.models.workflow_version import (
    TriggerType,
    WorkflowVersion,
)
from cerebrum.repositories.contracts import FilterOperator, FilterSpec, Page, Pagination
from cerebrum.repositories.postgres.workflow_repository import WorkflowRepository
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException


class WorkflowService:
    def __init__(
        self,
        *,
        workflow_repository: WorkflowRepository,
        workflow_version_repository: WorkflowVersionRepository,
        event_dispatcher: EventDispatcher,
        audit_service: AuditService,
    ) -> None:
        self._workflows = workflow_repository
        self._versions = workflow_version_repository
        self._events = event_dispatcher
        self._audit = audit_service

    async def create(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        name: str,
        description: str | None,
        trigger_type: TriggerType | str,
        trigger_config: dict[str, Any] | None,
        steps: list[dict[str, Any]],
        created_by: uuid.UUID,
        metadata: dict[str, Any] | None = None,
        is_template: bool = False,
    ) -> Workflow:
        trigger_type_value = (
            trigger_type.value
            if isinstance(trigger_type, TriggerType)
            else str(trigger_type)
        )
        trigger_config = trigger_config or {}
        errors = validate_trigger(trigger_type_value, trigger_config) + validate_steps(
            steps
        )
        if errors:
            raise ValidationException(
                "Invalid workflow definition.", context={"errors": errors}
            )

        workflow = Workflow(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name=name,
            description=description,
            status=WorkflowStatus.ACTIVE.value,
            is_template=is_template,
            workflow_metadata=metadata or {},
            created_by=created_by,
        )
        await self._workflows.add(workflow)

        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=1,
            trigger_type=trigger_type_value,
            trigger_config=trigger_config,
            steps=steps,
            created_by=created_by,
        )
        await self._versions.add(version)

        workflow.current_version_id = version.id
        await self._workflows.update(workflow)

        self._events.publish(
            WorkflowCreatedEvent(workflow_id=workflow.id, workspace_id=workspace_id)
        )
        await self._audit.record(
            AuditEventType.WORKFLOW_CREATED,
            user_id=created_by,
            organization_id=organization_id,
            workspace_id=workspace_id,
            metadata={"workflow_id": str(workflow.id)},
        )
        return workflow

    async def get(self, workflow_id: uuid.UUID, *, workspace_id: uuid.UUID) -> Workflow:
        workflow = await self._workflows.get_by_id(workflow_id)
        if workflow is None or workflow.workspace_id != workspace_id:
            raise NotFoundException(f"No workflow with id {workflow_id}.")
        return workflow

    async def get_current_version(self, workflow: Workflow) -> WorkflowVersion:
        if workflow.current_version_id is None:
            raise ValidationException(f"Workflow {workflow.id} has no current version.")
        version = await self._versions.get_by_id(workflow.current_version_id)
        if version is None:
            raise ValidationException(
                f"Workflow {workflow.id}'s current version is missing."
            )
        return version

    async def get_version(
        self, workflow_id: uuid.UUID, version_number: int, *, workspace_id: uuid.UUID
    ) -> WorkflowVersion:
        workflow = await self.get(workflow_id, workspace_id=workspace_id)
        version = await self._versions.get_by_number(workflow.id, version_number)
        if version is None:
            raise NotFoundException(
                f"No version {version_number} for workflow {workflow_id}."
            )
        return version

    async def list_versions(
        self, workflow_id: uuid.UUID, *, workspace_id: uuid.UUID, pagination: Pagination
    ) -> Page[WorkflowVersion]:
        workflow = await self.get(workflow_id, workspace_id=workspace_id)
        return await self._versions.list_by_workflow(workflow.id, pagination=pagination)

    async def update_definition(
        self,
        workflow_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        updated_by: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        trigger_type: TriggerType | str | None = None,
        trigger_config: dict[str, Any] | None = None,
        steps: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Workflow:
        """Always creates the next
        :class:`~cerebrum.infrastructure.database.models.workflow_version.WorkflowVersion`
        — a partial update (e.g. only ``steps``) is layered on top of
        the *current* version's ``trigger_type``/``trigger_config``,
        never a blank definition.
        """
        workflow = await self.get(workflow_id, workspace_id=workspace_id)
        current = await self.get_current_version(workflow)

        new_trigger_type = (
            (
                trigger_type.value
                if isinstance(trigger_type, TriggerType)
                else trigger_type
            )
            if trigger_type is not None
            else current.trigger_type
        )
        new_trigger_config = (
            trigger_config if trigger_config is not None else current.trigger_config
        )
        new_steps = steps if steps is not None else current.steps

        errors = validate_trigger(
            new_trigger_type, new_trigger_config
        ) + validate_steps(new_steps)
        if errors:
            raise ValidationException(
                "Invalid workflow definition.", context={"errors": errors}
            )

        version_number = await self._versions.get_next_version_number(workflow.id)
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=version_number,
            trigger_type=new_trigger_type,
            trigger_config=new_trigger_config,
            steps=new_steps,
            created_by=updated_by,
        )
        await self._versions.add(version)

        workflow.current_version_id = version.id
        if name is not None:
            workflow.name = name
        if description is not None:
            workflow.description = description
        if metadata is not None:
            workflow.workflow_metadata = metadata
        workflow.updated_by = updated_by
        await self._workflows.update(workflow)

        await self._audit.record(
            AuditEventType.WORKFLOW_UPDATED,
            user_id=updated_by,
            workspace_id=workspace_id,
            metadata={
                "workflow_id": str(workflow.id),
                "version_number": version_number,
            },
        )
        return workflow

    async def change_status(
        self,
        workflow_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        status: WorkflowStatus,
        updated_by: uuid.UUID,
    ) -> Workflow:
        workflow = await self.get(workflow_id, workspace_id=workspace_id)
        workflow.status = status.value
        workflow.updated_by = updated_by
        await self._workflows.update(workflow)
        await self._audit.record(
            AuditEventType.WORKFLOW_STATUS_CHANGED,
            user_id=updated_by,
            workspace_id=workspace_id,
            metadata={"workflow_id": str(workflow.id), "status": status.value},
        )
        return workflow

    async def delete(
        self, workflow_id: uuid.UUID, *, workspace_id: uuid.UUID, deleted_by: uuid.UUID
    ) -> None:
        workflow = await self.get(workflow_id, workspace_id=workspace_id)
        workflow.status = WorkflowStatus.ARCHIVED.value
        workflow.updated_by = deleted_by
        await self._workflows.update(workflow)
        await self._workflows.soft_delete(workflow_id)
        await self._audit.record(
            AuditEventType.WORKFLOW_DELETED,
            user_id=deleted_by,
            workspace_id=workspace_id,
            metadata={"workflow_id": str(workflow.id)},
        )

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        status: WorkflowStatus | None = None,
    ) -> Page[Workflow]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            FilterSpec(field="is_template", operator=FilterOperator.EQ, value=False),
        ]
        if status is not None:
            filters.append(
                FilterSpec(
                    field="status", operator=FilterOperator.EQ, value=status.value
                )
            )
        return await self._workflows.list(pagination=pagination, filters=filters)

    async def list_templates(
        self, *, workspace_id: uuid.UUID, pagination: Pagination
    ) -> Page[Workflow]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            ),
            FilterSpec(field="is_template", operator=FilterOperator.EQ, value=True),
        ]
        return await self._workflows.list(pagination=pagination, filters=filters)

    async def create_from_template(
        self,
        template_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        name: str,
        created_by: uuid.UUID,
    ) -> Workflow:
        template = await self._workflows.get_by_id(template_id)
        if (
            template is None
            or not template.is_template
            or template.workspace_id != workspace_id
        ):
            raise NotFoundException(f"No workflow template with id {template_id}.")
        version = await self.get_current_version(template)
        return await self.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name=name,
            description=template.description,
            trigger_type=version.trigger_type,
            trigger_config=version.trigger_config,
            steps=version.steps,
            metadata=dict(template.workflow_metadata),
            created_by=created_by,
        )
