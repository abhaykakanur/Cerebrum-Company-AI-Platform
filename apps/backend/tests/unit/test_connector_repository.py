"""Proves CIS Phase 5 Prompt 1's ``ConnectorRepository``,
``ConnectorSyncRunRepository``, and ``ConnectorSyncMappingRepository``
against a real SQLite-backed session — the same "test the real SQL, not
a reimplementation of it" precedent
test_conversation_repository.py's docstring explains.
"""

import uuid
from datetime import timedelta

import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.infrastructure.database.models.connector import (
    Connector,
    ConnectorStatus,
)
from cerebrum.infrastructure.database.models.connector_sync_mapping import (
    ConnectorSyncMapping,
)
from cerebrum.infrastructure.database.models.connector_sync_run import (
    ConnectorSyncRun,
    SyncRunStatus,
    SyncType,
)
from cerebrum.repositories.contracts import Pagination
from cerebrum.repositories.postgres.connector_repository import ConnectorRepository
from cerebrum.repositories.postgres.connector_sync_mapping_repository import (
    ConnectorSyncMappingRepository,
)
from cerebrum.repositories.postgres.connector_sync_run_repository import (
    ConnectorSyncRunRepository,
)
from cerebrum.utils.clock import utcnow

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


def _connector(
    *, workspace_id: uuid.UUID, organization_id: uuid.UUID, **overrides
) -> Connector:
    defaults = {
        "workspace_id": workspace_id,
        "organization_id": organization_id,
        "connector_type": "github",
        "name": "Acme GitHub",
        "status": ConnectorStatus.ACTIVE.value,
        "auth_type": "personal_access_token",
        "credentials": {"token": "secret"},
        "config": {"owner": "acme", "repo": "widgets"},
    }
    defaults.update(overrides)
    return Connector(**defaults)


async def test_add_and_get_connector(db_session: AsyncSession) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    repository = ConnectorRepository(db_session)

    created = await repository.add(
        _connector(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()

    fetched = await repository.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Acme GitHub"


async def test_soft_delete_and_restore(db_session: AsyncSession) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    repository = ConnectorRepository(db_session)
    created = await repository.add(
        _connector(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()

    await repository.soft_delete(created.id)
    await db_session.commit()
    assert await repository.get_by_id(created.id) is None

    await repository.restore(created.id)
    await db_session.commit()
    assert await repository.get_by_id(created.id) is not None


async def test_list_due_for_sync_filters_correctly(db_session: AsyncSession) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    repository = ConnectorRepository(db_session)
    now = utcnow()

    due = await repository.add(
        _connector(
            workspace_id=workspace_id,
            organization_id=organization_id,
            sync_interval_seconds=3600,
            next_sync_at=now - timedelta(minutes=1),
        )
    )
    await repository.add(
        _connector(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name="Not due yet",
            sync_interval_seconds=3600,
            next_sync_at=now + timedelta(hours=1),
        )
    )
    await repository.add(
        _connector(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name="Manual only",
            sync_interval_seconds=None,
            next_sync_at=None,
        )
    )
    await repository.add(
        _connector(
            workspace_id=workspace_id,
            organization_id=organization_id,
            name="Paused",
            status=ConnectorStatus.PAUSED.value,
            sync_interval_seconds=60,
            next_sync_at=now - timedelta(minutes=1),
        )
    )
    await db_session.commit()

    results = await repository.list_due_for_sync(as_of=now)

    assert [c.id for c in results] == [due.id]


async def test_list_filters_by_workspace(db_session: AsyncSession) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    _, other_workspace_id, _ = await _tenant(db_session)
    repository = ConnectorRepository(db_session)
    await repository.add(
        _connector(workspace_id=workspace_id, organization_id=organization_id)
    )
    await repository.add(
        _connector(workspace_id=other_workspace_id, organization_id=organization_id)
    )
    await db_session.commit()

    from cerebrum.repositories.contracts import FilterOperator, FilterSpec

    page = await repository.list(
        pagination=Pagination(page=1, page_size=50),
        filters=[
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ],
    )

    assert len(page.items) == 1


async def test_sync_run_repository_latest_and_history(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    connector = await ConnectorRepository(db_session).add(
        _connector(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()
    repository = ConnectorSyncRunRepository(db_session)

    older = await repository.add(
        ConnectorSyncRun(
            connector_id=connector.id,
            workspace_id=workspace_id,
            sync_type=SyncType.INITIAL.value,
            status=SyncRunStatus.COMPLETED.value,
            started_at=utcnow() - timedelta(hours=1),
            triggered_by=user_id,
        )
    )
    newer = await repository.add(
        ConnectorSyncRun(
            connector_id=connector.id,
            workspace_id=workspace_id,
            sync_type=SyncType.INCREMENTAL.value,
            status=SyncRunStatus.FAILED.value,
            started_at=utcnow(),
            cursor="page-3",
            triggered_by=user_id,
        )
    )
    await db_session.commit()

    latest = await repository.get_latest_for_connector(connector.id)
    assert latest is not None
    assert latest.id == newer.id

    latest_failed = await repository.get_latest_failed_for_connector(connector.id)
    assert latest_failed is not None
    assert latest_failed.cursor == "page-3"

    history = await repository.list_by_connector(
        connector.id, pagination=Pagination(page=1, page_size=50)
    )
    assert history.total_items == 2
    assert [run.id for run in history.items] == [newer.id, older.id]


async def test_sync_mapping_repository_get_by_external_id(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, _user_id = await _tenant(db_session)
    connector = await ConnectorRepository(db_session).add(
        _connector(workspace_id=workspace_id, organization_id=organization_id)
    )
    await db_session.commit()
    repository = ConnectorSyncMappingRepository(db_session)

    await repository.add(
        ConnectorSyncMapping(
            connector_id=connector.id,
            workspace_id=workspace_id,
            external_id="acme/widgets#1",
            content_checksum="abc123",
        )
    )
    await db_session.commit()

    found = await repository.get_by_external_id(connector.id, "acme/widgets#1")
    assert found is not None
    assert found.content_checksum == "abc123"

    missing = await repository.get_by_external_id(connector.id, "does-not-exist")
    assert missing is None

    all_mappings = await repository.list_by_connector(connector.id)
    assert len(all_mappings) == 1
