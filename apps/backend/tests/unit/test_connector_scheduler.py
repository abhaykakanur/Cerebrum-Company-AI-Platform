"""Proves CIS Phase 5 Prompt 1's ``ConnectorScheduler`` — Scheduled
Sync/Periodic Sync: it runs every connector
:meth:`~cerebrum.repositories.postgres.connector_repository.ConnectorRepository.list_due_for_sync`
reports due (see that method's tests in test_connector_repository.py for
the due-filtering rules themselves, not re-proven here), triggers each
as an unattributed (``triggered_by=None``) Incremental Sync, and can be
narrowed to one workspace.
"""

import uuid
from datetime import timedelta

import httpx
import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.connectors.connector_service import ConnectorService
from cerebrum.application.connectors.connector_sync_service import ConnectorSyncService
from cerebrum.application.connectors.scheduler import ConnectorScheduler
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.upload_service import UploadService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.config.documents import DocumentSettings
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.connector import (
    ConnectorAuthType,
    ConnectorType,
)
from cerebrum.infrastructure.database.models.connector_sync_run import SyncRunStatus
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


class _FakeKnowledgePreparationService:
    async def prepare(self, *args, **kwargs):
        return None


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


class _AuditRepo:
    async def add(self, entity):  # type: ignore[no-untyped-def]
        return entity


class _NoOpKnowledgePreparationService:
    async def prepare(self, version_id, *, workspace_id, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("no items should be processed in these scheduler tests")


def _scheduler(session: AsyncSession) -> ConnectorScheduler:
    audit = AuditService(_AuditRepo())
    connector_repository = ConnectorRepository(session)
    connector_service = ConnectorService(
        connector_repository=connector_repository,
        event_dispatcher=EventDispatcher(),
        audit_service=audit,
    )
    document_service = DocumentService(
        document_repository=DocumentRepository(session),
        folder_repository=FolderRepository(session),
        tag_repository=TagRepository(session),
        label_repository=LabelRepository(session),
    )
    upload_service = UploadService(
        version_service=VersionService(
            version_repository=DocumentVersionRepository(session),
            metadata_repository=DocumentMetadataRepository(session),
            document_repository=DocumentRepository(session),
        ),
        document_repository=DocumentRepository(session),
        uploader=_FakeUploader(),  # type: ignore[arg-type]
        virus_scanner=NoOpVirusScanner(),
        settings=DocumentSettings(max_file_size_bytes=1_000_000, allowed_mime_types=[]),
        audit_service=audit,
        preparation_service=_FakeKnowledgePreparationService(),  # type: ignore[arg-type]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    sync_service = ConnectorSyncService(
        connector_service=connector_service,
        sync_run_repository=ConnectorSyncRunRepository(session),
        sync_mapping_repository=ConnectorSyncMappingRepository(session),
        document_service=document_service,
        upload_service=upload_service,
        knowledge_preparation_service=_NoOpKnowledgePreparationService(),  # type: ignore[arg-type]
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        event_dispatcher=EventDispatcher(),
        audit_service=audit,
    )
    return ConnectorScheduler(
        connector_repository=connector_repository, sync_service=sync_service
    )


async def test_run_due_syncs_triggers_only_due_connectors(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    scheduler = _scheduler(db_session)
    connector_service = scheduler._sync_service._connectors

    due = await connector_service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Due connector",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()
    due.next_sync_at = utcnow() - timedelta(minutes=1)
    await connector_service._connectors.update(due)
    await db_session.commit()

    not_due = await connector_service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Not due connector",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "other"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()
    not_due.next_sync_at = utcnow() + timedelta(hours=1)
    await connector_service._connectors.update(not_due)
    await db_session.commit()

    runs = await scheduler.run_due_syncs()
    await db_session.commit()

    assert len(runs) == 1
    assert runs[0].connector_id == due.id
    assert runs[0].triggered_by is None
    assert runs[0].status == SyncRunStatus.COMPLETED.value


async def test_run_due_syncs_filters_by_workspace(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    _, other_workspace_id, other_user_id = await _tenant(db_session)
    scheduler = _scheduler(db_session)
    connector_service = scheduler._sync_service._connectors

    in_workspace = await connector_service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="In workspace",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()
    in_workspace.next_sync_at = utcnow() - timedelta(minutes=1)
    await connector_service._connectors.update(in_workspace)

    in_other_workspace = await connector_service.register(
        workspace_id=other_workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="In other workspace",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=other_user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()
    in_other_workspace.next_sync_at = utcnow() - timedelta(minutes=1)
    await connector_service._connectors.update(in_other_workspace)
    await db_session.commit()

    runs = await scheduler.run_due_syncs(workspace_id=workspace_id)
    await db_session.commit()

    assert len(runs) == 1
    assert runs[0].connector_id == in_workspace.id


async def test_list_due_delegates_to_repository(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    scheduler = _scheduler(db_session)
    connector_service = scheduler._sync_service._connectors

    connector = await connector_service.register(
        workspace_id=workspace_id,
        organization_id=organization_id,
        connector_type=ConnectorType.GITHUB,
        name="Due connector",
        auth_type=ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        credentials={"token": "secret"},
        config={"owner": "acme", "repo": "widgets"},
        created_by=user_id,
        sync_interval_seconds=3600,
    )
    await db_session.commit()
    connector.next_sync_at = utcnow() - timedelta(minutes=1)
    await connector_service._connectors.update(connector)
    await db_session.commit()

    due = await scheduler.list_due()

    assert [c.id for c in due] == [connector.id]
