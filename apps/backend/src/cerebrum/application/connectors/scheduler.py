"""``ConnectorScheduler``: CIS Phase 5 Prompt 1's Connector Scheduler /
Scheduled Sync (Periodic Sync). Computes which connectors are due
(:attr:`~cerebrum.infrastructure.database.models.connector.Connector.next_sync_at`
has arrived) and runs their next sync — but does not itself run on a
timer: no background worker runtime exists yet in this codebase (see
cerebrum.config.worker.WorkerSettings, ``enabled=False`` — "no worker
implementation exists at this milestone"), so Periodic Sync today means
"call :meth:`run_due_syncs` and every eligible connector catches up,"
whether that call comes from an operator/cron hitting the API endpoint
this backs, or a future phase's real worker loop. This mirrors
cerebrum.application.connectors.connector_repository.ConnectorRepository.list_due_for_sync's
own "a query to poll, not a timer to own" framing.
"""

import uuid

from cerebrum.application.connectors.connector_sync_service import ConnectorSyncService
from cerebrum.infrastructure.database.models.connector import Connector
from cerebrum.infrastructure.database.models.connector_sync_run import (
    ConnectorSyncRun,
    SyncType,
)
from cerebrum.repositories.postgres.connector_repository import ConnectorRepository
from cerebrum.utils.clock import utcnow


class ConnectorScheduler:
    def __init__(
        self,
        *,
        connector_repository: ConnectorRepository,
        sync_service: ConnectorSyncService,
    ) -> None:
        self._connectors = connector_repository
        self._sync_service = sync_service

    async def list_due(self) -> list[Connector]:
        return await self._connectors.list_due_for_sync(as_of=utcnow())

    async def run_due_syncs(
        self, *, workspace_id: uuid.UUID | None = None
    ) -> list[ConnectorSyncRun]:
        """Runs :meth:`~ConnectorSyncService.start_sync` (as an
        Incremental Sync, ``triggered_by=None`` — Scheduled Sync has no
        acting user) for every due connector, optionally narrowed to
        one workspace (an operator triggering their own workspace's
        due connectors rather than every tenant's).
        """
        due = await self.list_due()
        if workspace_id is not None:
            due = [
                connector for connector in due if connector.workspace_id == workspace_id
            ]

        runs = []
        for connector in due:
            run = await self._sync_service.start_sync(
                connector.id,
                workspace_id=connector.workspace_id,
                triggered_by=None,
                sync_type=SyncType.INCREMENTAL,
            )
            runs.append(run)
        return runs
