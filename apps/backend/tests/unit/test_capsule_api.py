"""HTTP-level proof that CIS Phase 5 Prompt 3's Employee Knowledge
Capsule API routes (cerebrum.api.v1.capsules) are wired correctly:
create, list, get, delete, link, update profile, refresh, timeline,
AI capsule, successor plan, compare, expertise/ownership search,
organizational knowledge map, and risk (bus factor/coverage/critical
dependencies). Same ``app.dependency_overrides`` pattern established by
test_workflow_api.py.

``get_employee_knowledge_capsule_service`` transitively depends on
``Neo4jDep`` (unreachable live infra in a unit-test environment, per
test_workflow_api.py's identical precedent) — overridden for every
request in this file with a service backed by the same real,
SQLite-backed ``db_session`` used to seed each test's tenant, and a
no-op fake in place of the real Neo4j mirror.
``get_risk_analysis_service``/``get_successor_planning_service`` need
no such override — neither touches Neo4j.
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
from cerebrum.application.capsules.capsule_graph_service import CapsuleGraphService
from cerebrum.application.capsules.employee_knowledge_capsule_service import (
    EmployeeKnowledgeCapsuleService,
)
from cerebrum.application.capsules.expertise_inference_service import (
    ExpertiseInferenceService,
)
from cerebrum.application.capsules.organizational_memory_service import (
    OrganizationalMemoryService,
)
from cerebrum.application.capsules.ownership_inference_service import (
    OwnershipInferenceService,
)
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.capsules import get_employee_knowledge_capsule_service
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
from cerebrum.infrastructure.database.models.relationship import (
    Relationship,
    RelationshipType,
)
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.capsule_evidence_repository import (
    CapsuleEvidenceRepository,
)
from cerebrum.repositories.postgres.capsule_repository import CapsuleRepository
from cerebrum.repositories.postgres.capsule_timeline_repository import (
    CapsuleTimelineRepository,
)
from cerebrum.repositories.postgres.entity_repository import EntityRepository
from cerebrum.repositories.postgres.relationship_repository import (
    RelationshipRepository,
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
    for code in ["capsules:read", "capsules:write"]:
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
    return org.id, workspace.id, user


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


async def _tenant_headers(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
):  # type: ignore[no-untyped-def]
    organization_id, workspace_id, user = await _seed_full_access_tenant(
        db_session, hasher
    )
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )
    return organization_id, workspace_id, user, headers


class _FakeGraphRepository:
    async def upsert_entity_node(self, **kwargs: Any) -> None:
        pass

    async def upsert_relationship_edge(self, **kwargs: Any) -> None:
        pass


def _capsule_service(session: AsyncSession) -> EmployeeKnowledgeCapsuleService:
    events = EventDispatcher()
    audit = AuditService(AuditEventRepository(session))
    entity_service = EntityService(entity_repository=EntityRepository(session))
    relationship_service = RelationshipService(
        relationship_repository=RelationshipRepository(session)
    )
    capsule_graph = CapsuleGraphService(
        entity_service=entity_service,
        relationship_service=relationship_service,
        graph_repository=_FakeGraphRepository(),  # type: ignore[arg-type]
    )
    return EmployeeKnowledgeCapsuleService(
        capsule_repository=CapsuleRepository(session),
        evidence_repository=CapsuleEvidenceRepository(session),
        timeline_repository=CapsuleTimelineRepository(session),
        capsule_graph_service=capsule_graph,
        expertise_service=ExpertiseInferenceService(
            relationship_service=relationship_service, entity_service=entity_service
        ),
        ownership_service=OwnershipInferenceService(
            relationship_service=relationship_service,
            entity_service=entity_service,
            capsule_graph_service=capsule_graph,
        ),
        memory_service=OrganizationalMemoryService(),
        relationship_service=relationship_service,
        entity_service=entity_service,
        event_dispatcher=events,
        audit_service=audit,
    )


@pytest.fixture(autouse=True)
def capsule_dependency_overrides(
    app: FastAPI, db_session: AsyncSession
) -> Iterator[None]:
    service = _capsule_service(db_session)
    app.dependency_overrides[get_employee_knowledge_capsule_service] = lambda: service
    yield
    del app.dependency_overrides[get_employee_knowledge_capsule_service]


async def _seed_person_with_evidence(
    db_session: AsyncSession, *, workspace_id: uuid.UUID, organization_id: uuid.UUID
) -> uuid.UUID:
    person = Entity(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.PERSON.value,
        canonical_name="Alice Example",
    )
    repo = Entity(
        workspace_id=workspace_id,
        organization_id=organization_id,
        entity_type=EntityType.CUSTOM.value,
        custom_type_name="repository",
        canonical_name="acme/widgets",
    )
    db_session.add_all([person, repo])
    await db_session.flush()
    for _ in range(5):
        db_session.add(
            Relationship(
                workspace_id=workspace_id,
                organization_id=organization_id,
                source_entity_id=person.id,
                target_entity_id=repo.id,
                relationship_type=RelationshipType.REFERENCES.value,
                confidence=0.9,
            )
        )
    await db_session.commit()
    return person.id


async def test_create_and_get_capsule(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    _, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )

    response = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["user_id"] == str(user.id)
    assert body["is_stale"] is True

    get_response = db_client.get(f"/api/v1/capsules/{body['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == body["id"]


async def test_list_capsules(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    _, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    db_client.post("/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers)

    response = db_client.get("/api/v1/capsules", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_link_and_refresh_capsule(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    organization_id, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]
    person_id = await _seed_person_with_evidence(
        db_session, workspace_id=workspace_id, organization_id=organization_id
    )

    link_response = db_client.post(
        f"/api/v1/capsules/{created['id']}/link",
        json={"entity_id": str(person_id)},
        headers=headers,
    )
    assert link_response.status_code == 200, link_response.text
    assert link_response.json()["data"]["person_entity_id"] == str(person_id)

    refresh_response = db_client.post(
        f"/api/v1/capsules/{created['id']}/refresh", headers=headers
    )
    assert refresh_response.status_code == 200, refresh_response.text
    refreshed = refresh_response.json()["data"]
    assert refreshed["is_stale"] is False
    assert len(refreshed["ownership_map"]) == 1
    assert refreshed["ownership_map"][0]["canonical_name"] == "acme/widgets"


async def test_update_profile(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    _, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]

    response = db_client.patch(
        f"/api/v1/capsules/{created['id']}/profile",
        json={
            "organizational_role": "Staff Engineer",
            "responsibilities": ["Platform"],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["organizational_role"] == "Staff Engineer"
    assert body["responsibilities"] == ["Platform"]


async def test_delete_capsule(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    _, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]

    delete_response = db_client.delete(
        f"/api/v1/capsules/{created['id']}", headers=headers
    )
    assert delete_response.status_code == 204

    get_response = db_client.get(f"/api/v1/capsules/{created['id']}", headers=headers)
    assert get_response.status_code == 404


async def test_timeline_ai_capsule_and_successor_plan(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    organization_id, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]
    person_id = await _seed_person_with_evidence(
        db_session, workspace_id=workspace_id, organization_id=organization_id
    )
    db_client.post(
        f"/api/v1/capsules/{created['id']}/link",
        json={"entity_id": str(person_id)},
        headers=headers,
    )
    db_client.post(f"/api/v1/capsules/{created['id']}/refresh", headers=headers)

    timeline_response = db_client.get(
        f"/api/v1/capsules/{created['id']}/timeline", headers=headers
    )
    assert timeline_response.status_code == 200
    assert len(timeline_response.json()["data"]) > 0

    ai_capsule_response = db_client.get(
        f"/api/v1/capsules/{created['id']}/ai-capsule", headers=headers
    )
    assert ai_capsule_response.status_code == 200
    ai_body = ai_capsule_response.json()["data"]
    assert ai_body["graph_references"]["person_entity_id"] == str(person_id)

    successor_response = db_client.get(
        f"/api/v1/capsules/{created['id']}/successor-plan", headers=headers
    )
    assert successor_response.status_code == 200, successor_response.text
    plan = successor_response.json()["data"]
    assert plan["critical_repositories"][0]["canonical_name"] == "acme/widgets"


async def test_compare_and_search_endpoints(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    organization_id, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]
    person_id = await _seed_person_with_evidence(
        db_session, workspace_id=workspace_id, organization_id=organization_id
    )
    db_client.post(
        f"/api/v1/capsules/{created['id']}/link",
        json={"entity_id": str(person_id)},
        headers=headers,
    )
    db_client.post(f"/api/v1/capsules/{created['id']}/refresh", headers=headers)

    other_user_id = uuid.uuid4()
    db_client.post(
        "/api/v1/capsules", json={"user_id": str(other_user_id)}, headers=headers
    )

    compare_response = db_client.get(
        "/api/v1/capsules/compare",
        params={"user_id_a": str(user.id), "user_id_b": str(other_user_id)},
        headers=headers,
    )
    assert compare_response.status_code == 200, compare_response.text
    assert "acme/widgets" in compare_response.json()["data"]["unique_ownership_a"]

    ownership_search_response = db_client.get(
        "/api/v1/capsules/search/ownership",
        params={"query": "widgets"},
        headers=headers,
    )
    assert ownership_search_response.status_code == 200
    assert len(ownership_search_response.json()["data"]) == 1

    map_response = db_client.get(
        "/api/v1/capsules/organizational-knowledge-map", headers=headers
    )
    assert map_response.status_code == 200
    assert len(map_response.json()["data"]) == 2


async def test_risk_endpoints(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    organization_id, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]
    person_id = await _seed_person_with_evidence(
        db_session, workspace_id=workspace_id, organization_id=organization_id
    )
    db_client.post(
        f"/api/v1/capsules/{created['id']}/link",
        json={"entity_id": str(person_id)},
        headers=headers,
    )
    db_client.post(f"/api/v1/capsules/{created['id']}/refresh", headers=headers)

    ownership_map = db_client.get(
        f"/api/v1/capsules/{created['id']}", headers=headers
    ).json()["data"]["ownership_map"]
    repo_entity_id = ownership_map[0]["entity_id"]

    bus_factor_response = db_client.get(
        f"/api/v1/capsules/risk/bus-factor/{repo_entity_id}", headers=headers
    )
    assert bus_factor_response.status_code == 200, bus_factor_response.text
    assert bus_factor_response.json()["data"]["bus_factor"] == 1
    assert bus_factor_response.json()["data"]["risk_level"] == "high"

    coverage_response = db_client.get("/api/v1/capsules/risk/coverage", headers=headers)
    assert coverage_response.status_code == 200
    assert coverage_response.json()["data"]["total_owned_entities"] >= 1

    critical_response = db_client.get(
        "/api/v1/capsules/risk/critical-dependencies", headers=headers
    )
    assert critical_response.status_code == 200
    assert critical_response.json()["data"] == []


async def test_workspace_isolation_hides_other_workspace_capsule(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    _, workspace_id, user, headers = await _tenant_headers(
        db_client, db_session, hasher
    )
    created = db_client.post(
        "/api/v1/capsules", json={"user_id": str(user.id)}, headers=headers
    ).json()["data"]

    _, _, _, other_headers = await _tenant_headers(db_client, db_session, hasher)
    response = db_client.get(f"/api/v1/capsules/{created['id']}", headers=other_headers)

    assert response.status_code == 404
