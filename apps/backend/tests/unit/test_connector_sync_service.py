"""Proves CIS Phase 5 Prompt 1's sync engine,
``ConnectorSyncService``: Delta Detection (both the cheap timestamp
pre-check and the authoritative checksum comparison), Conflict
Handling, Retry, Resume Failed Sync, and the full reuse-not-duplicate
pipeline handoff into ``DocumentService``/``UploadService``/a faked
``KnowledgePreparationService`` (mirroring
test_knowledge_preparation_api.py's ``_FakeKnowledgePreparationService``
precedent — this milestone only needs to prove the *handoff* happens,
not re-prove the pipeline itself, which CIS Phase 2/3 already covers).

:meth:`ConnectorSyncService._sync_item` is exercised directly with a
minimal fake adapter (Python's ``Connector`` Protocol is structural, so
no subclassing is required) for delta/conflict/retry cases where full
control over fetched content is needed. :meth:`ConnectorSyncService.start_sync`
is exercised end-to-end through the real ``GitHubConnector`` adapter
over ``httpx.MockTransport`` (mirroring test_connectors.py) to prove
the run-level orchestration: paging, run-status transitions, event
publication, audit logging, and cursor-based resume.
"""

import hashlib
import uuid
from datetime import timedelta

import httpx
import pytest
from _auth_factories import create_organization, create_user, create_workspace
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.connectors.connector_service import ConnectorService
from cerebrum.application.connectors.connector_sync_service import ConnectorSyncService
from cerebrum.application.connectors.events import SyncCompletedEvent, SyncFailedEvent
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.upload_service import UploadService
from cerebrum.application.knowledge.version_service import VersionService
from cerebrum.config.documents import DocumentSettings
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.connectors.base import (
    ConnectorContent,
    ConnectorError,
    ConnectorItem,
    ConnectorPage,
)
from cerebrum.infrastructure.database.models.connector import (
    ConnectorAuthType,
    ConnectorStatus,
    ConnectorType,
)
from cerebrum.infrastructure.database.models.connector_sync_mapping import (
    ConnectorSyncMapping,
    MappingSyncStatus,
)
from cerebrum.infrastructure.database.models.connector_sync_run import (
    SyncRunStatus,
)
from cerebrum.infrastructure.database.models.document_manifest import (
    DocumentManifest,
    ManifestStatus,
)
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
from cerebrum.utils.clock import ensure_utc, utcnow

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


class _FakeKnowledgePreparationService:
    def __init__(self) -> None:
        self.calls: list[uuid.UUID] = []

    async def prepare(
        self, version_id: uuid.UUID, *, workspace_id: uuid.UUID, **_kwargs: object
    ) -> DocumentManifest:
        self.calls.append(version_id)
        return DocumentManifest(
            id=uuid.uuid4(),
            document_version_id=version_id,
            extraction_id=uuid.uuid4(),
            status=ManifestStatus.READY.value,
            chunking_strategy="recursive",
            chunk_count=1,
            total_character_count=10,
            statistics={},
            error_message=None,
            created_at=utcnow(),
            updated_at=utcnow(),
        )


class _FakeAdapter:
    connector_type = "github"

    def __init__(
        self,
        *,
        content_by_id: dict[str, ConnectorContent] | None = None,
        fail_ids: set[str] | None = None,
    ) -> None:
        self._content_by_id = content_by_id or {}
        self._fail_ids = fail_ids or set()
        self.fetch_calls: list[str] = []

    async def test_connection(self, *, credentials, config) -> bool:  # type: ignore[no-untyped-def]
        return True

    async def list_changes(  # type: ignore[no-untyped-def]
        self, *, credentials, config, since=None, cursor=None, limit=50
    ) -> ConnectorPage:
        return ConnectorPage(items=[], next_cursor=None)

    async def fetch_content(  # type: ignore[no-untyped-def]
        self, *, credentials, config, item: ConnectorItem
    ) -> ConnectorContent:
        self.fetch_calls.append(item.external_id)
        if item.external_id in self._fail_ids:
            raise ConnectorError("fetch failed")
        return self._content_by_id[item.external_id]


def _sync_service(
    session: AsyncSession,
    *,
    http_client: httpx.AsyncClient,
    events: EventDispatcher | None = None,
    knowledge_preparation: _FakeKnowledgePreparationService | None = None,
) -> ConnectorSyncService:
    audit = AuditService(_AuditRepo())
    connector_service = ConnectorService(
        connector_repository=ConnectorRepository(session),
        event_dispatcher=events or EventDispatcher(),
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
    )
    return ConnectorSyncService(
        connector_service=connector_service,
        sync_run_repository=ConnectorSyncRunRepository(session),
        sync_mapping_repository=ConnectorSyncMappingRepository(session),
        document_service=document_service,
        upload_service=upload_service,
        knowledge_preparation_service=knowledge_preparation
        or _FakeKnowledgePreparationService(),  # type: ignore[arg-type]
        http_client=http_client,
        event_dispatcher=events or EventDispatcher(),
        audit_service=audit,
    )


class _AuditRepo:
    async def add(self, entity):  # type: ignore[no-untyped-def]
        return entity


def _http_client(handler) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _register_github_connector(
    service: ConnectorSyncService,
    *,
    workspace_id,
    organization_id,
    user_id,
    **overrides,
):  # type: ignore[no-untyped-def]
    kwargs = {
        "workspace_id": workspace_id,
        "organization_id": organization_id,
        "connector_type": ConnectorType.GITHUB,
        "name": "Acme GitHub",
        "auth_type": ConnectorAuthType.PERSONAL_ACCESS_TOKEN,
        "credentials": {"token": "secret"},
        "config": {"owner": "acme", "repo": "widgets"},
        "created_by": user_id,
    }
    kwargs.update(overrides)
    return await service._connectors.register(**kwargs)


# --- _sync_item: Delta Detection / Conflict Handling / Retry ---------------


async def test_sync_item_creates_document_and_prepares_pipeline(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    knowledge_preparation = _FakeKnowledgePreparationService()
    service = _sync_service(
        db_session,
        http_client=_http_client(lambda r: httpx.Response(200, json={})),
        knowledge_preparation=knowledge_preparation,
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()

    item = ConnectorItem(
        external_id="acme/widgets#1",
        title="Bug report",
        kind="issue",
        external_url="https://github.com/acme/widgets/issues/1",
        updated_at=utcnow(),
    )
    adapter = _FakeAdapter(
        content_by_id={
            "acme/widgets#1": ConnectorContent(
                content=b"issue body", content_type="text/markdown", filename="1.md"
            )
        }
    )

    outcome = await service._sync_item(
        connector=connector,
        adapter=adapter,  # type: ignore[arg-type]
        credentials=None,  # type: ignore[arg-type]
        item=item,
        effective_user_id=user_id,
        workspace_id=workspace_id,
    )
    await db_session.commit()

    assert outcome == "processed"
    assert len(knowledge_preparation.calls) == 1
    mapping = await ConnectorSyncMappingRepository(db_session).get_by_external_id(
        connector.id, "acme/widgets#1"
    )
    assert mapping is not None
    assert mapping.sync_status == MappingSyncStatus.SYNCED.value
    assert mapping.document_id is not None


async def test_sync_item_skips_when_source_timestamp_not_newer(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _sync_service(
        db_session, http_client=_http_client(lambda r: httpx.Response(200, json={}))
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()
    now = utcnow()
    existing_mapping = await ConnectorSyncMappingRepository(db_session).add(
        ConnectorSyncMapping(
            connector_id=connector.id,
            workspace_id=workspace_id,
            external_id="acme/widgets#1",
            external_updated_at=now,
            content_checksum="abc",
            document_id=uuid.uuid4(),
        )
    )
    await db_session.commit()

    item = ConnectorItem(
        external_id="acme/widgets#1",
        title="Bug report",
        kind="issue",
        updated_at=now - timedelta(minutes=5),
    )
    adapter = _FakeAdapter()

    outcome = await service._sync_item(
        connector=connector,
        adapter=adapter,  # type: ignore[arg-type]
        credentials=None,  # type: ignore[arg-type]
        item=item,
        effective_user_id=user_id,
        workspace_id=workspace_id,
    )

    assert outcome == "skipped"
    assert adapter.fetch_calls == []
    assert existing_mapping.content_checksum == "abc"


async def test_sync_item_skips_via_checksum_when_content_unchanged(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _sync_service(
        db_session, http_client=_http_client(lambda r: httpx.Response(200, json={}))
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()
    now = utcnow()
    content = b"unchanged body"
    checksum = hashlib.sha256(content).hexdigest()
    await ConnectorSyncMappingRepository(db_session).add(
        ConnectorSyncMapping(
            connector_id=connector.id,
            workspace_id=workspace_id,
            external_id="acme/widgets#1",
            external_updated_at=now - timedelta(hours=1),
            content_checksum=checksum,
            document_id=uuid.uuid4(),
        )
    )
    await db_session.commit()

    item = ConnectorItem(
        external_id="acme/widgets#1",
        title="Bug report",
        kind="issue",
        updated_at=now,
    )
    adapter = _FakeAdapter(
        content_by_id={
            "acme/widgets#1": ConnectorContent(
                content=content, content_type="text/markdown", filename="1.md"
            )
        }
    )

    outcome = await service._sync_item(
        connector=connector,
        adapter=adapter,  # type: ignore[arg-type]
        credentials=None,  # type: ignore[arg-type]
        item=item,
        effective_user_id=user_id,
        workspace_id=workspace_id,
    )
    await db_session.commit()

    assert outcome == "skipped"
    assert adapter.fetch_calls == ["acme/widgets#1"]
    mapping = await ConnectorSyncMappingRepository(db_session).get_by_external_id(
        connector.id, "acme/widgets#1"
    )
    assert mapping is not None
    assert ensure_utc(mapping.external_updated_at) == now


async def test_sync_item_marks_failed_after_retries_exhausted(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _sync_service(
        db_session, http_client=_http_client(lambda r: httpx.Response(200, json={}))
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()

    item = ConnectorItem(
        external_id="acme/widgets#2",
        title="Flaky item",
        kind="issue",
        updated_at=utcnow(),
    )
    adapter = _FakeAdapter(fail_ids={"acme/widgets#2"})

    outcome = await service._sync_item(
        connector=connector,
        adapter=adapter,  # type: ignore[arg-type]
        credentials=None,  # type: ignore[arg-type]
        item=item,
        effective_user_id=user_id,
        workspace_id=workspace_id,
    )

    assert outcome == "failed"
    assert adapter.fetch_calls == ["acme/widgets#2", "acme/widgets#2"]


async def test_sync_item_marks_failed_on_upload_conflict(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    service = _sync_service(
        db_session, http_client=_http_client(lambda r: httpx.Response(200, json={}))
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()

    duplicate_content = b"identical content"
    existing_document = await service._documents.create(
        workspace_id=workspace_id,
        folder_id=None,
        name="Pre-existing.md",
        created_by=user_id,
    )
    await service._uploads.upload_new_version(
        existing_document.id,
        workspace_id=workspace_id,
        filename="pre-existing.md",
        content_type="text/markdown",
        content=duplicate_content,
        created_by=user_id,
    )
    await db_session.commit()

    item = ConnectorItem(
        external_id="acme/widgets#3",
        title="Duplicate item",
        kind="issue",
        updated_at=utcnow(),
    )
    adapter = _FakeAdapter(
        content_by_id={
            "acme/widgets#3": ConnectorContent(
                content=duplicate_content, content_type="text/markdown", filename="3.md"
            )
        }
    )

    outcome = await service._sync_item(
        connector=connector,
        adapter=adapter,  # type: ignore[arg-type]
        credentials=None,  # type: ignore[arg-type]
        item=item,
        effective_user_id=user_id,
        workspace_id=workspace_id,
    )
    await db_session.commit()

    assert outcome == "failed"
    mapping = await ConnectorSyncMappingRepository(db_session).get_by_external_id(
        connector.id, "acme/widgets#3"
    )
    assert mapping is not None
    assert mapping.sync_status == MappingSyncStatus.FAILED.value


# --- start_sync: run-level orchestration (real GitHubConnector adapter) ----


def _github_issue(number: int, *, updated_at: str, body: str = "body text") -> dict:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": body,
        "html_url": f"https://github.com/acme/widgets/issues/{number}",
        "updated_at": updated_at,
    }


async def test_start_sync_completes_single_page(db_session: AsyncSession) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    completed: list[SyncCompletedEvent] = []
    events.subscribe(SyncCompletedEvent, completed.append)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[_github_issue(1, updated_at="2026-01-01T00:00:00Z")]
        )

    service = _sync_service(
        db_session, http_client=_http_client(handler), events=events
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()

    run = await service.start_sync(
        connector.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == SyncRunStatus.COMPLETED.value
    assert run.items_processed == 1
    assert run.items_discovered == 1
    assert len(completed) == 1

    refreshed = await service._connectors.get(connector.id, workspace_id=workspace_id)
    assert refreshed.status == ConnectorStatus.ACTIVE.value
    assert refreshed.last_successful_sync_at is not None


async def test_start_sync_marks_failed_on_connector_error(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    events = EventDispatcher()
    failed: list[SyncFailedEvent] = []
    events.subscribe(SyncFailedEvent, failed.append)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "server error"})

    service = _sync_service(
        db_session, http_client=_http_client(handler), events=events
    )
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()

    run = await service.start_sync(
        connector.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert run.status == SyncRunStatus.FAILED.value
    assert run.error_message is not None
    assert len(failed) == 1

    refreshed = await service._connectors.get(connector.id, workspace_id=workspace_id)
    assert refreshed.status == ConnectorStatus.ERROR.value


async def test_start_sync_resume_continues_from_saved_cursor(
    db_session: AsyncSession,
) -> None:
    organization_id, workspace_id, user_id = await _tenant(db_session)
    page_one = [_github_issue(1, updated_at="2026-01-01T00:00:00Z")] * 50
    calls: list[str] = []

    def failing_handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        calls.append(page or "1")
        if page == "2":
            return httpx.Response(500, json={"message": "server error"})
        return httpx.Response(200, json=page_one)

    service = _sync_service(db_session, http_client=_http_client(failing_handler))
    connector = await _register_github_connector(
        service,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    await db_session.commit()

    first_run = await service.start_sync(
        connector.id, workspace_id=workspace_id, triggered_by=user_id
    )
    await db_session.commit()

    assert first_run.status == SyncRunStatus.FAILED.value
    assert first_run.cursor == "2"

    def resumed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[_github_issue(51, updated_at="2026-01-02T00:00:00Z")]
        )

    service_resumed = _sync_service(
        db_session, http_client=_http_client(resumed_handler)
    )
    second_run = await service_resumed.start_sync(
        connector.id,
        workspace_id=workspace_id,
        triggered_by=user_id,
        resume=True,
    )
    await db_session.commit()

    assert second_run.status == SyncRunStatus.COMPLETED.value
    assert second_run.items_processed == 1
