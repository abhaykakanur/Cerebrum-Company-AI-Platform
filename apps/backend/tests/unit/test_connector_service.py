"""Proves CIS Phase 5 Prompt 1's ``ConnectorService``: registration
(with Connector Validation), Workspace Isolation, Configuration
(including the "leave unset fields unchanged" sentinel), Lifecycle
status changes, sync bookkeeping (``record_sync_success``/``_failure``),
Connector Health checks, and Secret Isolation/Audit Logging around
credential access — against a real, SQLite-backed
``ConnectorRepository`` (see test_connector_repository.py's docstring
for why) and a real ``AuditService``.
"""

import uuid

import httpx
import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.connectors.connector_service import ConnectorService
from cerebrum.application.connectors.events import (
    ConnectorHealthyEvent,
    ConnectorRegisteredEvent,
    ConnectorUnhealthyEvent,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.infrastructure.database.models.connector import (
    ConnectorAuthType,
    ConnectorStatus,
    ConnectorType,
)
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.audit_repository import AuditEventRepository
from cerebrum.repositories.postgres.connector_repository import ConnectorRepository
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException

pytestmark = pytest.mark.unit


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
) -> ConnectorService:
    return ConnectorService(
        connector_repository=ConnectorRepository(session),
        event_dispatcher=events or EventDispatcher(),
        audit_service=AuditService(AuditEventRepository(session)),
    )


async def _last_audit_event(session: AsyncSession) -> AuditEvent:
    from sqlalchemy import select

    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1)
    )
    event = result.scalar_one()
    return event


async def test_register_creates_connector_and_publishes_event(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[ConnectorRegisteredEvent] = []
    events.subscribe(ConnectorRegisteredEvent, received.append)
    service = _service(db_session, events=events)

    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    assert connector.status == ConnectorStatus.ACTIVE.value
    assert connector.next_sync_at is None
    assert len(received) == 1
    audit_event = await _last_audit_event(db_session)
    assert audit_event.event_type == AuditEventType.CONNECTOR_REGISTERED.value


async def test_register_sets_next_sync_at_when_interval_given(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)

    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()

    assert connector.next_sync_at is not None


async def test_register_raises_when_config_incomplete(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)

    with pytest.raises(ValidationException):
        await service.register(
            workspace_id=workspace_id,
            organization_id=organization_id,
            connector_type=ConnectorType.GITHUB,
            name="Acme GitHub",
            auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
            credentials={},
            config={},
            created_by=user_id,
        )


async def test_get_raises_not_found_for_wrong_workspace(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(connector.id, workspace_id=uuid.uuid4())


async def test_configure_updates_only_provided_fields(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()
    original_next_sync_at = connector.next_sync_at

    updated = await service.configure(
        connector.id, workspace_id=workspace_id, updated_by=user_id, name="Renamed"
    )
    await db_session.commit()

    assert updated.name == "Renamed"
    assert updated.sync_interval_seconds == 3600
    assert updated.next_sync_at == original_next_sync_at


async def test_configure_setting_sync_interval_to_none_disables_it(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()

    updated = await service.configure(
        connector.id,
        workspace_id=workspace_id,
        updated_by=user_id,
        sync_interval_seconds=None,
    )
    await db_session.commit()

    assert updated.sync_interval_seconds is None
    assert updated.next_sync_at is None


async def test_configure_raises_when_result_is_invalid(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    with pytest.raises(ValidationException):
        await service.configure(
            connector.id, workspace_id=workspace_id, updated_by=user_id, config={}
        )


async def test_delete_soft_deletes_and_disables(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    await service.delete(connector.id, workspace_id=workspace_id, deleted_by=user_id)
    await db_session.commit()

    with pytest.raises(NotFoundException):
        await service.get(connector.id, workspace_id=workspace_id)


async def test_list_in_workspace_filters_by_status(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    active = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Active connector",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    paused = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.SLACK,
        name="Paused connector",
        auth_type=ConnectorAuthType.OAUTH2,
        credentials={"token": "secret"},
        config={"channel_id": "C1"},
        created_by=user_id,
    )
    await db_session.commit()
    await service.change_status(
        paused.id,
        workspace_id=workspace_id,
        status=ConnectorStatus.PAUSED,
        updated_by=user_id,
    )
    await db_session.commit()

    active_page = await service.list_in_workspace(
        workspace_id=workspace_id,
        pagination=Pagination(page=1, page_size=50),
        status=ConnectorStatus.ACTIVE,
    )

    assert [c.id for c in active_page.items] == [active.id]


async def test_get_credentials_wraps_and_audits(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "super-secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    credentials = await service.get_credentials(
        connector.id, workspace_id=workspace_id, accessed_by=user_id
    )
    await db_session.commit()

    assert credentials.get("token") == "super-secret"
    audit_event = await _last_audit_event(db_session)
    assert audit_event.event_type == AuditEventType.CONNECTOR_CREDENTIALS_ACCESSED.value


async def test_record_sync_success_updates_timestamps(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()

    updated = await service.record_sync_success(connector.id, workspace_id=workspace_id)
    await db_session.commit()

    assert updated.last_successful_sync_at is not None
    assert updated.next_sync_at is not None
    assert updated.status == ConnectorStatus.ACTIVE.value


async def test_record_sync_failure_sets_error_status(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _service(db_session)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    updated = await service.record_sync_failure(connector.id, workspace_id=workspace_id)
    await db_session.commit()

    assert updated.status == ConnectorStatus.ERROR.value


async def test_check_health_marks_healthy(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[ConnectorHealthyEvent] = []
    events.subscribe(ConnectorHealthyEvent, received.append)
    service = _service(db_session, events=events)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 1})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    updated = await service.check_health(
        connector.id, workspace_id=workspace_id, http_client=http_client
    )
    await db_session.commit()

    assert updated.health_status == "healthy"
    assert len(received) == 1


async def test_check_health_marks_unhealthy(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    received: list[ConnectorUnhealthyEvent] = []
    events.subscribe(ConnectorUnhealthyEvent, received.append)
    service = _service(db_session, events=events)
    connector = await service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Acme GitHub",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
    )
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    updated = await service.check_health(
        connector.id, workspace_id=workspace_id, http_client=http_client
    )
    await db_session.commit()

    assert updated.health_status == "unhealthy"
    assert updated.health_message is not None
    assert len(received) == 1
