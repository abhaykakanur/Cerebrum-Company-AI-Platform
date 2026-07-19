"""HTTP-level proof that CIS Phase 3 Prompt 1's Entity/Relationship/
Graph routes are wired correctly. CRUD hits the real database directly
(no Neo4j involved); ``get_knowledge_graph_service`` is overridden with
a fake for the routes that touch the graph (delete/neighbors/
statistics/validate) — same ``app.dependency_overrides`` pattern
test_extraction_api.py/test_upload_api.py established, since real Neo4j
is unreachable in this sandbox.
"""

import uuid

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

from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.knowledge_graph import get_knowledge_graph_service
from cerebrum.infrastructure.security.password import PasswordHasher

pytestmark = pytest.mark.unit


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(SecuritySettings())


async def _seed_full_access_tenant(session: AsyncSession, hasher: PasswordHasher):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from cerebrum.infrastructure.database.models.role import Permission

    org = await create_organization(session, slug="acme")
    workspace = await create_workspace(session, organization_id=org.id)
    role = await create_role(session, organization_id=org.id)
    for code in [
        "entities:read",
        "entities:write",
        "entities:delete",
        "relationships:read",
        "relationships:write",
        "relationships:delete",
        "graph:read",
    ]:
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
        email="alice@acme.example",
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


class _FakeKnowledgeGraphService:
    def __init__(self) -> None:
        self.deleted_entity_ids: list[uuid.UUID] = []
        self.deleted_relationship_ids: list[uuid.UUID] = []
        self.neighbors = [
            {
                "id": str(uuid.uuid4()),
                "workspace_id": "ws",
                "entity_type": "person",
                "canonical_name": "Bob Williams",
                "aliases": [],
                "confidence": 0.6,
            }
        ]

    async def soft_delete_entity(self, entity_id, *, workspace_id):  # type: ignore[no-untyped-def]
        self.deleted_entity_ids.append(entity_id)

    async def soft_delete_relationship(self, relationship_id, *, workspace_id):  # type: ignore[no-untyped-def]
        self.deleted_relationship_ids.append(relationship_id)

    async def get_neighbors(self, entity_id, *, workspace_id, depth=1):  # type: ignore[no-untyped-def]
        return self.neighbors

    async def get_statistics(self, *, workspace_id):  # type: ignore[no-untyped-def]
        return {"entity_count": 3, "relationship_count": 2}

    async def validate_consistency(self, *, workspace_id):  # type: ignore[no-untyped-def]
        return []


async def test_entity_crud_round_trip(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    create_response = db_client.post(
        "/api/v1/entities",
        json={"entity_type": "organization", "canonical_name": "Acme Corp"},
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    entity_id = create_response.json()["data"]["id"]
    assert create_response.json()["data"]["confidence"] == 1.0

    get_response = db_client.get(f"/api/v1/entities/{entity_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["canonical_name"] == "Acme Corp"

    update_response = db_client.patch(
        f"/api/v1/entities/{entity_id}",
        json={"canonical_name": "Acme Corporation", "aliases": ["Acme"]},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["canonical_name"] == "Acme Corporation"
    assert update_response.json()["data"]["aliases"] == ["Acme"]

    list_response = db_client.get("/api/v1/entities", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    history_response = db_client.get(
        f"/api/v1/entities/{entity_id}/history", headers=headers
    )
    assert history_response.status_code == 200
    assert history_response.json()["data"]["provenance"] == []


async def test_entity_delete_propagates_through_knowledge_graph_service(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )
    create_response = db_client.post(
        "/api/v1/entities",
        json={"entity_type": "person", "canonical_name": "Alice"},
        headers=headers,
    )
    entity_id = create_response.json()["data"]["id"]

    fake_graph = _FakeKnowledgeGraphService()
    app.dependency_overrides[get_knowledge_graph_service] = lambda: fake_graph
    try:
        delete_response = db_client.delete(
            f"/api/v1/entities/{entity_id}", headers=headers
        )
    finally:
        del app.dependency_overrides[get_knowledge_graph_service]

    assert delete_response.status_code == 204
    assert fake_graph.deleted_entity_ids == [uuid.UUID(entity_id)]


async def test_entity_neighbors_endpoint(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    fake_graph = _FakeKnowledgeGraphService()
    app.dependency_overrides[get_knowledge_graph_service] = lambda: fake_graph
    try:
        response = db_client.get(
            f"/api/v1/entities/{uuid.uuid4()}/neighbors?depth=2", headers=headers
        )
    finally:
        del app.dependency_overrides[get_knowledge_graph_service]

    assert response.status_code == 200
    assert response.json()["data"][0]["canonical_name"] == "Bob Williams"


async def test_relationship_crud_round_trip(
    db_client: TestClient, db_session: AsyncSession, hasher: PasswordHasher
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    alice = db_client.post(
        "/api/v1/entities",
        json={"entity_type": "person", "canonical_name": "Alice"},
        headers=headers,
    ).json()["data"]
    bob = db_client.post(
        "/api/v1/entities",
        json={"entity_type": "person", "canonical_name": "Bob"},
        headers=headers,
    ).json()["data"]

    create_response = db_client.post(
        "/api/v1/relationships",
        json={
            "source_entity_id": alice["id"],
            "target_entity_id": bob["id"],
            "relationship_type": "reports_to",
        },
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    relationship_id = create_response.json()["data"]["id"]

    get_response = db_client.get(
        f"/api/v1/relationships/{relationship_id}", headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["relationship_type"] == "reports_to"

    update_response = db_client.patch(
        f"/api/v1/relationships/{relationship_id}",
        json={"confidence": 0.5},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["confidence"] == 0.5


async def test_relationship_delete_propagates_through_knowledge_graph_service(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    fake_graph = _FakeKnowledgeGraphService()
    app.dependency_overrides[get_knowledge_graph_service] = lambda: fake_graph
    try:
        relationship_id = uuid.uuid4()
        response = db_client.delete(
            f"/api/v1/relationships/{relationship_id}", headers=headers
        )
    finally:
        del app.dependency_overrides[get_knowledge_graph_service]

    assert response.status_code == 204
    assert fake_graph.deleted_relationship_ids == [relationship_id]


async def test_graph_statistics_and_validate_endpoints(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    workspace_id, user = await _seed_full_access_tenant(db_session, hasher)
    headers = _login(
        db_client,
        email=user.email,
        password="CorrectHorse123!",
        workspace_id=workspace_id,
    )

    fake_graph = _FakeKnowledgeGraphService()
    app.dependency_overrides[get_knowledge_graph_service] = lambda: fake_graph
    try:
        statistics_response = db_client.get("/api/v1/graph/statistics", headers=headers)
        validate_response = db_client.get("/api/v1/graph/validate", headers=headers)
    finally:
        del app.dependency_overrides[get_knowledge_graph_service]

    assert statistics_response.status_code == 200
    assert statistics_response.json()["data"] == {
        "entity_count": 3,
        "relationship_count": 2,
    }
    assert validate_response.status_code == 200
    assert validate_response.json()["data"] == {"is_consistent": True, "issues": []}
