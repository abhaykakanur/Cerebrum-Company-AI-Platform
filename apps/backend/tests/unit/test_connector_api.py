"""HTTP-level proof that CIS Phase 5 Prompt 1's Connector API routes
(cerebrum.api.v1.connectors) are wired correctly: register, list, get,
configure, delete, health, start sync, stop sync, sync status, sync
history. Same ``app.dependency_overrides`` pattern established by
test_conversation_api.py.

``get_connector_sync_service`` transitively depends on
``MinIODep``/``Neo4jDep``/``QdrantDep``/``OpenSearchDep`` — resolved
*eagerly* by FastAPI before the route body runs (unreachable live infra
in a unit-test environment, per test_conversation_api.py's identical
precedent) — so it is overridden for every request in this file with a
sync service backed by the same real, SQLite-backed ``db_session`` used
to seed each test's tenant. ``get_http_client`` is likewise overridden
so the health-check route's real ``GitHubConnector`` adapter talks to
an ``httpx.MockTransport`` instead of the real GitHub API.
"""

import uuid
from collections.abc import Iterator

import httpx
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
from cerebrum.application.connectors.connector_service import ConnectorService
from cerebrum.application.connectors.connector_sync_service import ConnectorSyncService
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.upload_service import UploadService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.config.documents import DocumentSettings
from cerebrum.config.security import SecuritySettings
from cerebrum.dependencies.connectors import get_connector_sync_service
from cerebrum.dependencies.infrastructure import get_http_client
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.security.password import PasswordHasher
from cerebrum.infrastructure.security.virus_scan import NoOpVirusScanner
from cerebrum.infrastructure.storage.files import UploadedFile
from cerebrum.repositories.postgres.connector_repository import ConnectorRepository
from cerebrum.repositories.postgres.connector_sync_mapping_repository import (
    ConnectorSyncMappingRepository,
)
from cerebrum.repositories.postgres.connector_sync_run_repository import (
    ConnectorSyncRunRepository,
)
from cerebrum.repositories.postgres.document_metadata_repository import (
    DocumentMetadataRepository,
)
from cerebrum.repositories.postgres.document_repository import DocumentRepository
from cerebrum.repositories.postgres.document_version_repository import (
    DocumentVersionRepository,
)
from cerebrum.repositories.postgres.folder_repository import FolderRepository
from cerebrum.repositories.postgres.label_repository import LabelRepository
from cerebrum.repositories.postgres.tag_repository import TagRepository

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
    for code in ["connectors:read", "connectors:write"]:
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


class _FakeUploader:
    async def upload(
        self, *, object_key: str, content: bytes, content_type: str, size_bytes: int
    ) -> UploadedFile:
        return UploadedFile(
            object_key=object_key,
            filename=object_key.rsplit("/", 1)[-1],
            content_type=content_type,
            size_bytes=size_bytes,
        )

    async def delete(self, object_key: str) -> None:
        pass

    async def presigned_upload_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str:
        return f"https://fake.example/{object_key}"


class _NoOpKnowledgePreparationService:
    async def prepare(self, version_id, *, workspace_id, **_kwargs):  # type: ignore[no-untyped-def]
        return None


class _AuditRepo:
    async def add(self, entity):  # type: ignore[no-untyped-def]
        return entity


def _github_list_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/issues"):
        return httpx.Response(200, json=[])
    return httpx.Response(200, json={"id": 1})


@pytest.fixture(autouse=True)
def connector_dependency_overrides(
    app: FastAPI, db_session: AsyncSession
) -> Iterator[None]:
    audit = AuditService(_AuditRepo())
    connector_service = ConnectorService(
        connector_repository=ConnectorRepository(db_session),
        event_dispatcher=EventDispatcher(),
        audit_service=audit,
    )
    document_service = DocumentService(
        document_repository=DocumentRepository(db_session),
        folder_repository=FolderRepository(db_session),
        tag_repository=TagRepository(db_session),
        label_repository=LabelRepository(db_session),
    )
    upload_service = UploadService(
        version_service=VersionService(
            version_repository=DocumentVersionRepository(db_session),
            metadata_repository=DocumentMetadataRepository(db_session),
            document_repository=DocumentRepository(db_session),
        ),
        document_repository=DocumentRepository(db_session),
        uploader=_FakeUploader(),  # type: ignore[arg-type]
        virus_scanner=NoOpVirusScanner(),
        settings=DocumentSettings(max_file_size_bytes=1_000_000, allowed_mime_types=[]),
        audit_service=audit,
    )
    sync_service = ConnectorSyncService(
        connector_service=connector_service,
        sync_run_repository=ConnectorSyncRunRepository(db_session),
        sync_mapping_repository=ConnectorSyncMappingRepository(db_session),
        document_service=document_service,
        upload_service=upload_service,
        knowledge_preparation_service=_NoOpKnowledgePreparationService(),  # type: ignore[arg-type]
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(_github_list_handler)
        ),
        event_dispatcher=EventDispatcher(),
        audit_service=audit,
    )
    app.dependency_overrides[get_connector_sync_service] = lambda: sync_service
    app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(_github_list_handler)
    )
    yield
    del app.dependency_overrides[get_connector_sync_service]
    del app.dependency_overrides[get_http_client]


def _register_payload(**overrides) -> dict:  # type: ignore[no-untyped-def]
    payload = {
        "connector_type": "github",
        "name": "Acme GitHub",
        "auth_type": "personal_access_token",
        "credentials": {"token": "secret"},
        "config": {"owner": "acme", "repo": "widgets"},
    }
    payload.update(overrides)
    return payload


async def test_register_and_get_connector(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)

    response = db_client.post(
        "/api/v1/connectors", json=_register_payload(), headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["connector_type"] == "github"
    assert body["status"] == "active"
    assert "credentials" not in body

    get_response = db_client.get(f"/api/v1/connectors/{body['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == body["id"]


async def test_register_rejects_incomplete_config(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)

    response = db_client.post(
        "/api/v1/connectors",
        json=_register_payload(config={}, credentials={}),
        headers=headers,
    )

    assert response.status_code == 422, response.text


async def test_list_connectors_filters_by_status(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    db_client.post("/api/v1/connectors", json=_register_payload(), headers=headers)

    response = db_client.get(
        "/api/v1/connectors", params={"connector_status": "active"}, headers=headers
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_configure_connector_updates_name(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/connectors", json=_register_payload(), headers=headers
    ).json()["data"]

    response = db_client.patch(
        f"/api/v1/connectors/{created['id']}",
        json={"name": "Renamed connector"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["name"] == "Renamed connector"


async def test_delete_connector(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/connectors", json=_register_payload(), headers=headers
    ).json()["data"]

    delete_response = db_client.delete(
        f"/api/v1/connectors/{created['id']}", headers=headers
    )
    assert delete_response.status_code == 204

    get_response = db_client.get(f"/api/v1/connectors/{created['id']}", headers=headers)
    assert get_response.status_code == 404


async def test_check_connector_health(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/connectors", json=_register_payload(), headers=headers
    ).json()["data"]

    response = db_client.get(
        f"/api/v1/connectors/{created['id']}/health", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["health_status"] == "healthy"


async def test_start_sync_and_get_status_and_history(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/connectors", json=_register_payload(), headers=headers
    ).json()["data"]

    sync_response = db_client.post(
        f"/api/v1/connectors/{created['id']}/sync", json={}, headers=headers
    )
    assert sync_response.status_code == 200, sync_response.text
    run = sync_response.json()["data"]
    assert run["status"] == "completed"

    status_response = db_client.get(
        f"/api/v1/connectors/{created['id']}/sync/{run['id']}", headers=headers
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["id"] == run["id"]

    history_response = db_client.get(
        f"/api/v1/connectors/{created['id']}/sync-history", headers=headers
    )
    assert history_response.status_code == 200
    assert len(history_response.json()["data"]) == 1


async def test_workspace_isolation_hides_other_workspace_connector(
    app: FastAPI,
    db_client: TestClient,
    db_session: AsyncSession,
    hasher: PasswordHasher,
) -> None:
    headers = await _headers(db_client, db_session, hasher)
    created = db_client.post(
        "/api/v1/connectors", json=_register_payload(), headers=headers
    ).json()["data"]

    other_headers = await _headers(db_client, db_session, hasher)
    response = db_client.get(
        f"/api/v1/connectors/{created['id']}", headers=other_headers
    )

    assert response.status_code == 404
