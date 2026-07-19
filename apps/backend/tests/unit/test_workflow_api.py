"""HTTP-level proof that CIS Phase 5 Prompt 2's Workflow API routes
(cerebrum.api.v1.workflows) are wired correctly: create, list, get,
update, delete, pause, resume, versions, execute, run history/status/
steps, cancel, retry, templates, and schedules. Same
``app.dependency_overrides`` pattern established by
test_connector_api.py.

``get_workflow_run_service``/``get_workflow_scheduler`` transitively
depend on ``MinIODep``/``Neo4jDep``/``QdrantDep``/``OpenSearchDep``/
``RedisDep`` — resolved *eagerly* by FastAPI before the route body runs
(unreachable live infra in a unit-test environment, per
test_connector_api.py's identical precedent) — so both are overridden
for every request in this file with services backed by the same real,
SQLite-backed ``db_session`` used to seed each test's tenant, and every
step executor replaced by a no-op fake (the execution engine itself is
already covered end-to-end by test_workflow_run_service.py; this file
only needs to prove the HTTP routes reach the right service methods).
"""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from _auth_factories import (
    create_membership,
    create_organization,
    create_permission,
    create_role,
    create_user,
    create_workspace,
    grant_permission_to_role,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.workflows.scheduler import WorkflowScheduler
from cerebrum.application.workflows.step_executors import StepOutcome
from cerebrum.application.workflows.workflow_run_service import WorkflowRunService
from cerebrum.application.workflows.workflow_service import WorkflowService
from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.workflows import (
    get_workflow_run_service,
    get_workflow_scheduler,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.workflow_version import StepType
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.workflow_repository import WorkflowRepository
from cerebrum.repositories.postgres.workflow_run_repository import WorkflowRunRepository
from cerebrum.repositories.postgres.workflow_schedule_repository import (
    WorkflowScheduleRepository,
)
from cerebrum.repositories.postgres.workflow_step_run_repository import (
    WorkflowStepRunRepository,
)
from cerebrum.repositories.postgres.workflow_version_repository import (
    WorkflowVersionRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


async def _seed_full_access_tenant(session: AsyncSession, hasher: PasswordHasher):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from cerebrum.infrastructure.database.models.role import Permission

    unique = uuid.uuid4().hex[:8]
    org = await create_organization(session, slug=f"acme-{unique}")
    workspace = await create_workspace(session, organization_id=org.id)
    role = await create_role(session, organization_id=org.id)
    for code in ["workflows:read", "workflows:write"]:
        existing = await session.execute(
            select(Permission).where(Permission.code == code)
        )
        permission = existing.scalar_one_or_none()
        if permission is None:
            permission = await create_permission(session, code=code)
        await grant_permission_to_role(
            session, role_id=role.id, permission_id=permission.id
        )
    user = await create_user(
        session,
        organization_id=org.id,
        email=f"alice-{unique}@acme.example",
        password="CorrectHorse123!",
        hasher=hasher,
    )
    await create_membership(
        session, user_id=user.id, workspace_id=workspace.id, role_id=role.id
    )
    await session.commit()
    return workspace.id, user


def _login(
    client: TestClient, *, email: str, password: str, workspace_id: uuid.UUID
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
        "X-Workspace-ID": str(workspace_id),
    }


async def _headers(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> dict[str, str]:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    return _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )


class _NoOpExecutor:
    async def execute(  # type: ignore[no-untyped-def]
        self, config: dict[str, Any], *, workspace_id, triggered_by, context
    ) -> StepOutcome:
        return StepOutcome(output={"ok": True})


def _workflow_service(
    session: AsyncSession, events: EventDispatcher
) -> WorkflowService:
    return WorkflowService(
        workflow_repository=WorkflowRepository(session),
        workflow_version_repository=WorkflowVersionRepository(session),
        event_dispatcher=events,
        audit_service=AuditService(AuditEventRepository(session)),
    )


def _run_service(session: AsyncSession, events: EventDispatcher) -> WorkflowRunService:
    return WorkflowRunService(
        workflow_service=_workflow_service(session, events),
        workflow_version_repository=WorkflowVersionRepository(session),
        workflow_run_repository=WorkflowRunRepository(session),
        workflow_step_run_repository=WorkflowStepRunRepository(session),
        step_executors={step_type: _NoOpExecutor() for step_type in StepType},  # type: ignore[misc]
        event_dispatcher=events,
        audit_service=AuditService(AuditEventRepository(session)),
    )


@pytest.fixture(autouse=True)
def workflow_dependency_overrides(
    app: FastAPI, db_session: AsyncSession
) -> Iterator[None]:
    events = EventDispatcher()
    run_service = _run_service(db_session, events)
    scheduler = WorkflowScheduler(
        schedule_repository=WorkflowScheduleRepository(db_session),
        run_service=run_service,
        audit_service=AuditService(AuditEventRepository(db_session)),
    )
    app.dependency_overrides[get_workflow_run_service] = lambda: run_service
    app.dependency_overrides[get_workflow_scheduler] = lambda: scheduler
    yield
    del app.dependency_overrides[get_workflow_run_service]
    del app.dependency_overrides[get_workflow_scheduler]


def _create_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Nightly digest",
        "description": "Summarizes overnight activity.",
        "trigger_type": "manual",
        "trigger_config": {},
        "steps": [
            {"id": "notify", "type": "notification", "config": {"message": "hi"}}
        ],
    }
    payload.update(overrides)
    return payload


async def test_create_and_get_workflow(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)

    response = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["status"] == "active"
    assert body["current_version_id"] is not None

    get_response = db_client.get(f"/api/v1/workflows/{body['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == body["id"]


async def test_create_rejects_invalid_steps(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)

    response = db_client.post(
        "/api/v1/workflows",
        json=_create_payload(steps=[{"id": "a", "type": "ai_reasoning", "config": {}}]),
        headers=headers,
    )

    assert response.status_code == 422, response.text


async def test_list_workflows(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    db_client.post("/api/v1/workflows", json=_create_payload(), headers=headers)

    response = db_client.get("/api/v1/workflows", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_update_workflow_creates_new_version(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]

    response = db_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"name": "Renamed"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["name"] == "Renamed"

    versions_response = db_client.get(
        f"/api/v1/workflows/{created['id']}/versions", headers=headers
    )
    assert versions_response.status_code == 200
    assert len(versions_response.json()["data"]) == 2


async def test_pause_blocks_execution_and_resume_unblocks(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]

    pause_response = db_client.post(
        f"/api/v1/workflows/{created['id']}/pause", headers=headers
    )
    assert pause_response.status_code == 200
    assert pause_response.json()["data"]["status"] == "paused"

    blocked_execute = db_client.post(
        f"/api/v1/workflows/{created['id']}/execute", json={}, headers=headers
    )
    assert blocked_execute.status_code == 422

    resume_response = db_client.post(
        f"/api/v1/workflows/{created['id']}/resume", headers=headers
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["data"]["status"] == "active"


async def test_delete_workflow(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]

    delete_response = db_client.delete(
        f"/api/v1/workflows/{created['id']}", headers=headers
    )
    assert delete_response.status_code == 204

    get_response = db_client.get(f"/api/v1/workflows/{created['id']}", headers=headers)
    assert get_response.status_code == 404


async def test_execute_and_get_run_status_and_history_and_steps(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]

    execute_response = db_client.post(
        f"/api/v1/workflows/{created['id']}/execute", json={}, headers=headers
    )
    assert execute_response.status_code == 200, execute_response.text
    run = execute_response.json()["data"]
    assert run["status"] == "completed"

    status_response = db_client.get(
        f"/api/v1/workflows/{created['id']}/runs/{run['id']}", headers=headers
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["id"] == run["id"]

    history_response = db_client.get(
        f"/api/v1/workflows/{created['id']}/runs", headers=headers
    )
    assert history_response.status_code == 200
    assert len(history_response.json()["data"]) == 1

    steps_response = db_client.get(
        f"/api/v1/workflows/{created['id']}/runs/{run['id']}/steps", headers=headers
    )
    assert steps_response.status_code == 200
    assert len(steps_response.json()["data"]) == 1
    assert steps_response.json()["data"][0]["status"] == "completed"


async def test_cancel_run(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]
    run = db_client.post(
        f"/api/v1/workflows/{created['id']}/execute", json={}, headers=headers
    ).json()["data"]

    cancel_response = db_client.post(
        f"/api/v1/workflows/{created['id']}/runs/{run['id']}/cancel", headers=headers
    )

    assert cancel_response.status_code == 422, cancel_response.text


async def test_retry_run(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]
    run = db_client.post(
        f"/api/v1/workflows/{created['id']}/execute", json={}, headers=headers
    ).json()["data"]

    retry_response = db_client.post(
        f"/api/v1/workflows/{created['id']}/runs/{run['id']}/retry", headers=headers
    )

    assert retry_response.status_code == 422, retry_response.text


async def test_templates_list_and_instantiate(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    template = db_client.post(
        "/api/v1/workflows", json=_create_payload(is_template=True), headers=headers
    ).json()["data"]

    list_response = db_client.get("/api/v1/workflows/templates", headers=headers)
    assert list_response.status_code == 200
    assert [w["id"] for w in list_response.json()["data"]] == [template["id"]]

    instantiate_response = db_client.post(
        f"/api/v1/workflows/templates/{template['id']}/instantiate",
        json={"name": "From template"},
        headers=headers,
    )
    assert instantiate_response.status_code == 201, instantiate_response.text
    assert instantiate_response.json()["data"]["name"] == "From template"


async def test_create_list_and_delete_schedule(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows",
        json=_create_payload(trigger_type="scheduled"),
        headers=headers,
    ).json()["data"]

    create_response = db_client.post(
        f"/api/v1/workflows/{created['id']}/schedules",
        json={"schedule_type": "cron", "cron_expression": "*/5 * * * *"},
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    schedule = create_response.json()["data"]
    assert schedule["status"] == "active"

    list_response = db_client.get(
        f"/api/v1/workflows/{created['id']}/schedules", headers=headers
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    delete_response = db_client.delete(
        f"/api/v1/workflows/{created['id']}/schedules/{schedule['id']}", headers=headers
    )
    assert delete_response.status_code == 204

    list_after_delete = db_client.get(
        f"/api/v1/workflows/{created['id']}/schedules", headers=headers
    )
    assert list_after_delete.json()["data"] == []


async def test_workspace_isolation_hides_other_workspace_workflow(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/workflows", json=_create_payload(), headers=headers
    ).json()["data"]

    other_headers = await _headers(db_client, db_session, hasher)
    response = db_client.get(
        f"/api/v1/workflows/{created['id']}", headers=other_headers
    )

    assert response.status_code == 404
