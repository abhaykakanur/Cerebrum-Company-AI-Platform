"""Proves CIS Phase 5 Prompt 2's ``WorkflowService``: Workflow
Definition, Workflow Versioning (every definition change creates a new
immutable version), Workflow Validation, Lifecycle status changes,
Workspace Isolation, and Workflow Templates — against a real,
SQLite-backed ``WorkflowRepository``/``WorkflowVersionRepository`` (see
test_workflow_repository.py's docstring for why) and a real
``AuditService``.
"""

import uuid

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.events import WorkflowCreatedEvent
from cerebrum.application.workflows.workflow_service import WorkflowService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.infrastructure.database.models.workflow import WorkflowStatus
from cerebrum.infrastructure.database.models.workflow_version import TriggerType
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.workflow_repository import WorkflowRepository
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

pytestmark = pytest.mark.unit

_SIMPLE_STEPS = [{"id": "notify", "type": "notification", "config": {"message": "hi"}}]


def _hasher():  # type: ignore[no-untyped-def]
    from cerebrum.config.security import SecuritySettings
    from cerebrum.infrastructure.security.password import PasswordHasher

    return PasswordHasher(SecuritySettings())


async def _tenant(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    unique = uuid.uuid4().hex[:8]
    org = await create_organization(session, slug=f"acme-{unique}")
    workspace = await create_workspace(session, organization_id=org.id)
    user = await create_user(
        session,
        organization_id=org.id,
        email=f"alice-{unique}@acme.example",
        password="CorrectHorse123!",
        hasher=_hasher(),
    )
    await session.commit()
    return org.id, workspace.id, user.id


def _service(
    session: AsyncSession, *, events: EventDispatcher | None = None
) -> WorkflowService:
    return WorkflowService(
        workflow_repository=WorkflowRepository(session),
        workflow_version_repository=WorkflowVersionRepository(session),
        event_dispatcher=events or EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(session)),
    )


async def _last_audit_event(session: AsyncSession) -> AuditEvent:
    from sqlalchemy import select

    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1)
    )
    return result.scalar_one()


async def test_create_creates_workflow_and_first_version(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[WorkflowCreatedEvent] = []
    events.subscribe(WorkflowCreatedEvent, received.append)
    service = _service(db_session, events=events)

    workflow = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Nightly digest",
        description="Summarizes overnight activity.",
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    assert workflow.status == WorkflowStatus.ACTIVE.value
    assert workflow.current_version_id is not None
    assert len(received) == 1
    audit_event = await _last_audit_event(db_session)
    assert audit_event.event_type == AuditEventType.WORKFLOW_CREATED.value

    version = await service.get_current_version(workflow)
    assert version.version_number == 1
    assert version.steps == _SIMPLE_STEPS


async def test_create_rejects_invalid_steps(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)

    with pytest.raises(ValidationException):
        await service.create(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name="Broken",
            description=None,
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=[{"id": "a", "type": "ai_reasoning", "config": {}}],
            created_by=user_id,
        )


async def test_get_raises_not_found_for_wrong_workspace(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    workflow = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Nightly digest",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(workflow.id, workspace_id=uuid.uuid4())


async def test_update_definition_creates_new_version_and_layers_partial_update(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    workflow = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Nightly digest",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={"foo": "bar"},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    new_steps = [
        {"id": "notify", "type": "notification", "config": {"message": "updated"}}
    ]
    updated = await service.update_definition(
        workflow.id, workspace_id=workspace_id, updated_by=user_id, steps=new_steps
    )
    await db_session.commit()

    version = await service.get_current_version(updated)
    assert version.version_number == 2
    assert version.steps == new_steps
    # trigger_type/trigger_config were not part of this update — they
    # should carry forward from the previous version rather than reset.
    assert version.trigger_type == TriggerType.MANUAL.value
    assert version.trigger_config == {"foo": "bar"}

    versions_page = await service.list_versions(
        workflow.id,
        workspace_id=workspace_id,
        pagination=Pagination(page=1, page_size=50),
    )
    assert versions_page.total_items == 2


async def test_update_definition_rejects_invalid_result(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    workflow = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Nightly digest",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.update_definition(
            workflow.id, workspace_id=workspace_id, updated_by=user_id, steps=[]
        )


async def test_change_status_pauses_and_resumes(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    workflow = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Nightly digest",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    paused = await service.change_status(
        workflow.id,
        workspace_id=workspace_id,
        status=WorkflowStatus.PAUSED,
        updated_by=user_id,
    )
    await db_session.commit()
    assert paused.status == WorkflowStatus.PAUSED.value

    resumed = await service.change_status(
        workflow.id,
        workspace_id=workspace_id,
        status=WorkflowStatus.ACTIVE,
        updated_by=user_id,
    )
    await db_session.commit()
    assert resumed.status == WorkflowStatus.ACTIVE.value


async def test_delete_soft_deletes_and_archives(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    workflow = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Nightly digest",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    await service.delete(workflow.id, workspace_id=workspace_id, deleted_by=user_id)
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(workflow.id, workspace_id=workspace_id)


async def test_list_in_workspace_excludes_templates_and_filters_by_status(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    live = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Live workflow",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="A template",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
        is_template=True,
    )
    await db_session.commit()

    page = await service.list_in_workspace(
        workspace_id=workspace_id, pagination=Pagination(page=1, page_size=50)
    )
    assert [w.id for w in page.items] == [live.id]

    filtered = await service.list_in_workspace(
        workspace_id=workspace_id,
        pagination=Pagination(page=1, page_size=50),
        status=WorkflowStatus.PAUSED,
    )
    assert filtered.total_items == 0


async def test_list_templates_and_create_from_template(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    template = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Digest template",
        description="A reusable starting point.",
        trigger_type=TriggerType.MANUAL,
        trigger_config={"channel": "ops"},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
        is_template=True,
    )
    await db_session.commit()

    templates_page = await service.list_templates(
        workspace_id=workspace_id, pagination=Pagination(page=1, page_size=50)
    )
    assert [w.id for w in templates_page.items] == [template.id]

    instantiated = await service.create_from_template(
        template.id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="My digest",
        created_by=user_id,
    )
    await db_session.commit()

    assert instantiated.is_template is False
    version = await service.get_current_version(instantiated)
    assert version.steps == _SIMPLE_STEPS
    assert version.trigger_config == {"channel": "ops"}


async def test_create_from_template_rejects_non_template_workflow(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    regular = await service.create(
        workspace_id=workspace_id,
        organization_id=organization_id,
        name="Not a template",
        description=None,
        trigger_type=TriggerType.MANUAL,
        trigger_config={},
        steps=_SIMPLE_STEPS,
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.create_from_template(
            regular.id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            name="Clone",
            created_by=user_id,
        )
