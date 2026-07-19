"""``ConnectorSyncService``: CIS Phase 5 Prompt 1's sync engine — Initial
Sync, Incremental Sync, Delta Detection, Change Tracking, Version
Updates, Conflict Handling, Retry, Progress Tracking, Scheduled Sync,
Manual Sync, and Resume Failed Sync, all in one orchestrator whose only
job past "fetch a normalized item from a connector" is handing that
item to the *existing* CIS Phase 2/3 pipeline —
cerebrum.application.knowledge.document_service.DocumentService, then
cerebrum.application.knowledge.upload_service.UploadService, then
cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService
— see this milestone's OBJECTIVE: "Reuse all existing ingestion... Do
not duplicate processing logic."

**Delta Detection** (:meth:`_sync_item`) is two-layered: a cheap
timestamp pre-check (skip immediately if the source's own
``updated_at`` is no newer than what
:class:`~cerebrum.infrastructure.database.models.connector_sync_mapping.ConnectorSyncMapping`
already recorded) backed by an authoritative SHA256 content-hash
comparison after fetching (catches the common case of a source
misreporting or omitting ``updated_at``, and avoids ever creating a
no-op ``DocumentVersion`` for byte-identical content).

**Retry** is per-item, not per-request: :meth:`_fetch_with_retry`
attempts a connector's ``fetch_content`` up to twice before giving up on
that one item and continuing the run — a single flaky item never aborts
an entire sync. **Conflict Handling**: a checksum collision against a
*different* document (``UploadService`` raising ``ConflictException``)
is recorded as a failed item, not a fatal run error.

**Progress Tracking** persists ``items_discovered``/``processed``/
``skipped``/``failed`` on the
:class:`~cerebrum.infrastructure.database.models.connector_sync_run.ConnectorSyncRun`
row once per page (not once per item — this service runs synchronously
within one HTTP request/response cycle, since no background worker
runtime exists yet — see cerebrum.config.worker.WorkerSettings — so
sub-page granularity would add overhead no concurrent reader could
actually observe before the request's own transaction commits anyway).

A single :meth:`start_sync` call processes at most
``_MAX_PAGES_PER_RUN`` pages; if the source has more, the run's
``cursor`` is saved and a follow-up call with ``resume=True`` continues
from it — CIS Phase 5 Prompt 1's Resume Failed Sync, and the practical
answer to "no background worker exists to run an unbounded sync loop."
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any

import httpx

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.connectors.connector_service import ConnectorService
from cerebrum.application.connectors.events import (
    SyncCompletedEvent,
    SyncFailedEvent,
    SyncStartedEvent,
)
from cerebrum.application.knowledge.document_service import DocumentService
from cerebrum.application.knowledge.knowledge_preparation_service import (
    KnowledgePreparationService,
)
from cerebrum.application.knowledge.upload_service import UploadService
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.connectors.base import Connector as ConnectorAdapter
from cerebrum.infrastructure.connectors.base import (
    ConnectorContent,
    ConnectorCredentials,
    ConnectorError,
    ConnectorItem,
)
from cerebrum.infrastructure.connectors.registry import build_connector
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.connector import Connector, ConnectorType
from cerebrum.infrastructure.database.models.connector_sync_mapping import (
    ConnectorSyncMapping,
    MappingSyncStatus,
)
from cerebrum.infrastructure.database.models.connector_sync_run import (
    ConnectorSyncRun,
    SyncRunStatus,
    SyncType,
)
from cerebrum.repositories.contracts import Page, Pagination
from cerebrum.repositories.postgres.connector_sync_mapping_repository import (
    ConnectorSyncMappingRepository,
)
from cerebrum.repositories.postgres.connector_sync_run_repository import (
    ConnectorSyncRunRepository,
)
from cerebrum.shared.errors.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from cerebrum.utils.clock import ensure_utc, utcnow

_MAX_PAGES_PER_RUN = 10
_PAGE_SIZE = 50
_FETCH_ATTEMPTS = 2


class ConnectorSyncService:
    def __init__(
        self,
        *,
        connector_service: ConnectorService,
        sync_run_repository: ConnectorSyncRunRepository,
        sync_mapping_repository: ConnectorSyncMappingRepository,
        document_service: DocumentService,
        upload_service: UploadService,
        knowledge_preparation_service: KnowledgePreparationService,
        http_client: httpx.AsyncClient,
        event_dispatcher: EventDispatcher,
        audit_service: AuditService,
    ) -> None:
        self._connectors = connector_service
        self._sync_runs = sync_run_repository
        self._sync_mappings = sync_mapping_repository
        self._documents = document_service
        self._uploads = upload_service
        self._knowledge_preparation = knowledge_preparation_service
        self._http_client = http_client
        self._events = event_dispatcher
        self._audit = audit_service

    async def start_sync(
        self,
        connector_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
        sync_type: SyncType = SyncType.INCREMENTAL,
        resume: bool = False,
    ) -> ConnectorSyncRun:
        connector = await self._connectors.get(connector_id, workspace_id=workspace_id)
        credentials = await self._connectors.get_credentials(
            connector_id, workspace_id=workspace_id, accessed_by=triggered_by
        )
        adapter = build_connector(
            ConnectorType(connector.connector_type), http_client=self._http_client
        )
        effective_user_id = triggered_by or connector.created_by
        if effective_user_id is None:
            raise ValidationException(
                "Cannot run a sync for a connector with no attributable user."
            )

        since, cursor = await self._resolve_starting_point(
            connector, sync_type=sync_type, resume=resume
        )

        run = await self._sync_runs.add(
            ConnectorSyncRun(
                connector_id=connector_id,
                workspace_id=workspace_id,
                sync_type=sync_type.value,
                status=SyncRunStatus.RUNNING.value,
                started_at=utcnow(),
                triggered_by=triggered_by,
            )
        )
        self._events.publish(
            SyncStartedEvent(
                connector_id=connector_id,
                workspace_id=workspace_id,
                sync_run_id=run.id,
                sync_type=sync_type.value,
            )
        )
        await self._audit.record(
            AuditEventType.CONNECTOR_SYNC_STARTED,
            user_id=triggered_by,
            workspace_id=workspace_id,
            metadata={"connector_id": str(connector_id), "sync_run_id": str(run.id)},
        )

        try:
            await self._run_sync_loop(
                connector=connector,
                adapter=adapter,
                credentials=credentials,
                run=run,
                since=since,
                cursor=cursor,
                effective_user_id=effective_user_id,
                workspace_id=workspace_id,
            )
        except ConnectorError as exc:
            run.status = SyncRunStatus.FAILED.value
            run.error_message = str(exc)
            run.completed_at = utcnow()
            await self._sync_runs.update(run)
            await self._connectors.record_sync_failure(
                connector_id, workspace_id=workspace_id
            )
            self._events.publish(
                SyncFailedEvent(
                    connector_id=connector_id,
                    workspace_id=workspace_id,
                    sync_run_id=run.id,
                    error_message=str(exc),
                )
            )
            await self._audit.record(
                AuditEventType.CONNECTOR_SYNC_FAILED,
                user_id=triggered_by,
                workspace_id=workspace_id,
                metadata={
                    "connector_id": str(connector_id),
                    "sync_run_id": str(run.id),
                    "reason": str(exc),
                },
            )
            return run

        run.status = SyncRunStatus.COMPLETED.value
        run.completed_at = utcnow()
        await self._sync_runs.update(run)
        await self._connectors.record_sync_success(
            connector_id, workspace_id=workspace_id
        )
        self._events.publish(
            SyncCompletedEvent(
                connector_id=connector_id,
                workspace_id=workspace_id,
                sync_run_id=run.id,
                items_processed=run.items_processed,
                items_skipped=run.items_skipped,
                items_failed=run.items_failed,
            )
        )
        await self._audit.record(
            AuditEventType.CONNECTOR_SYNC_COMPLETED,
            user_id=triggered_by,
            workspace_id=workspace_id,
            metadata={
                "connector_id": str(connector_id),
                "sync_run_id": str(run.id),
                "items_processed": run.items_processed,
            },
        )
        return run

    async def get_run(
        self,
        connector_id: uuid.UUID,
        sync_run_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
    ) -> ConnectorSyncRun:
        await self._connectors.get(connector_id, workspace_id=workspace_id)
        run = await self._sync_runs.get_by_id(sync_run_id)
        if (
            run is None
            or run.connector_id != connector_id
            or run.workspace_id != workspace_id
        ):
            raise NotFoundException(f"No sync run with id {sync_run_id}.")
        return run

    async def list_runs(
        self,
        connector_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
    ) -> Page[ConnectorSyncRun]:
        await self._connectors.get(connector_id, workspace_id=workspace_id)
        return await self._sync_runs.list_by_connector(
            connector_id, pagination=pagination
        )

    async def stop_sync(
        self,
        connector_id: uuid.UUID,
        sync_run_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
    ) -> ConnectorSyncRun:
        """Marks a sync run terminated. Since a sync executes
        synchronously within one request (see this service's
        docstring), this cannot interrupt an in-flight call from
        another request — its real purpose is clearing a run stuck in
        ``RUNNING`` after a crashed process, so a fresh sync can start.
        """
        run = await self._sync_runs.get_by_id(sync_run_id)
        if (
            run is None
            or run.connector_id != connector_id
            or run.workspace_id != workspace_id
        ):
            raise NotFoundException(f"No sync run with id {sync_run_id}.")
        if run.status != SyncRunStatus.RUNNING.value:
            raise ValidationException("Only a running sync can be stopped.")
        run.status = SyncRunStatus.CANCELLED.value
        run.completed_at = utcnow()
        return await self._sync_runs.update(run)

    async def _resolve_starting_point(
        self, connector: Connector, *, sync_type: SyncType, resume: bool
    ) -> tuple[datetime | None, str | None]:
        if resume:
            failed_run = await self._sync_runs.get_latest_failed_for_connector(
                connector.id
            )
            if failed_run is not None and failed_run.cursor:
                return None, failed_run.cursor
        if sync_type in (SyncType.INCREMENTAL, SyncType.MANUAL):
            last_successful_sync_at = connector.last_successful_sync_at
            since = (
                None
                if last_successful_sync_at is None
                else ensure_utc(last_successful_sync_at)
            )
            return since, None
        return None, None

    async def _run_sync_loop(
        self,
        *,
        connector: Connector,
        adapter: ConnectorAdapter,
        credentials: ConnectorCredentials,
        run: ConnectorSyncRun,
        since: datetime | None,
        cursor: str | None,
        effective_user_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:
        for _ in range(_MAX_PAGES_PER_RUN):
            page = await adapter.list_changes(
                credentials=credentials,
                config=connector.config,
                since=since,
                cursor=cursor,
                limit=_PAGE_SIZE,
            )
            run.items_discovered += len(page.items)
            for item in page.items:
                outcome = await self._sync_item(
                    connector=connector,
                    adapter=adapter,
                    credentials=credentials,
                    item=item,
                    effective_user_id=effective_user_id,
                    workspace_id=workspace_id,
                )
                if outcome == "processed":
                    run.items_processed += 1
                elif outcome == "skipped":
                    run.items_skipped += 1
                else:
                    run.items_failed += 1

            cursor = page.next_cursor
            run.cursor = cursor
            await self._sync_runs.update(run)
            if cursor is None:
                break

    async def _sync_item(
        self,
        *,
        connector: Connector,
        adapter: ConnectorAdapter,
        credentials: ConnectorCredentials,
        item: ConnectorItem,
        effective_user_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> str:
        mapping = await self._sync_mappings.get_by_external_id(
            connector.id, item.external_id
        )
        if (
            mapping is not None
            and mapping.external_updated_at is not None
            and item.updated_at is not None
            and item.updated_at <= ensure_utc(mapping.external_updated_at)
        ):
            return "skipped"

        content = await self._fetch_with_retry(
            adapter, credentials=credentials, config=connector.config, item=item
        )
        if content is None:
            if mapping is not None:
                mapping.sync_status = MappingSyncStatus.FAILED.value
                await self._sync_mappings.update(mapping)
            return "failed"

        checksum = hashlib.sha256(content.content).hexdigest()
        if mapping is not None and mapping.content_checksum == checksum:
            mapping.external_updated_at = item.updated_at
            mapping.last_synced_at = utcnow()
            await self._sync_mappings.update(mapping)
            return "skipped"

        if mapping is None:
            document = await self._documents.create(
                workspace_id=workspace_id,
                folder_id=None,
                name=self._document_name(connector, item),
                created_by=effective_user_id,
            )
            mapping = await self._sync_mappings.add(
                ConnectorSyncMapping(
                    connector_id=connector.id,
                    workspace_id=workspace_id,
                    external_id=item.external_id,
                    external_url=item.external_url,
                    document_id=document.id,
                    sync_status=MappingSyncStatus.SYNCED.value,
                )
            )
        document_id = mapping.document_id
        assert document_id is not None

        try:
            version = await self._uploads.upload_new_version(
                document_id,
                workspace_id=workspace_id,
                filename=content.filename,
                content_type=content.content_type,
                content=content.content,
                created_by=effective_user_id,
                change_summary=f"Synced from {connector.connector_type}: {item.title}",
            )
        except ConflictException:
            mapping.sync_status = MappingSyncStatus.FAILED.value
            await self._sync_mappings.update(mapping)
            return "failed"

        await self._knowledge_preparation.prepare(version.id, workspace_id=workspace_id)

        mapping.external_url = item.external_url
        mapping.external_updated_at = item.updated_at
        mapping.content_checksum = checksum
        mapping.last_synced_at = utcnow()
        mapping.sync_status = MappingSyncStatus.SYNCED.value
        await self._sync_mappings.update(mapping)
        return "processed"

    @staticmethod
    async def _fetch_with_retry(
        adapter: ConnectorAdapter,
        *,
        credentials: ConnectorCredentials,
        config: dict[str, Any],
        item: ConnectorItem,
    ) -> ConnectorContent | None:
        for _attempt in range(_FETCH_ATTEMPTS):
            try:
                return await adapter.fetch_content(
                    credentials=credentials, config=config, item=item
                )
            except ConnectorError:
                continue
        return None

    @staticmethod
    def _document_name(connector: Connector, item: ConnectorItem) -> str:
        name = f"{connector.name}: {item.external_id} — {item.title}"
        return name[:255]
