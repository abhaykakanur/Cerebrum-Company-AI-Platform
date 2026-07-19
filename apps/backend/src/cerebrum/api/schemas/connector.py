"""Request/response schemas for CIS Phase 5 Prompt 1's Connector API.
Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` — see
cerebrum.api.schemas.knowledge's identical docstring precedent.

**Secret Isolation** (CIS Phase 5 Prompt 1's Security requirement) is
enforced structurally right here:
:class:`~cerebrum.infrastructure.database.models.connector.Connector.credentials`
has no corresponding field on :class:`ConnectorResponse` — there is no
code path by which a registered connector's secrets can be serialized
into an HTTP response, not a runtime check that could be bypassed.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel
from cerebrum.infrastructure.database.models.connector import (
    ConnectorAuthType,
    ConnectorType,
)
from cerebrum.infrastructure.database.models.connector_sync_run import SyncType

# --- Requests -----------------------------------------------------------------


class RegisterConnectorRequest(APIModel):
    connector_type: ConnectorType
    name: str = Field(min_length=1, max_length=255)
    auth_type: ConnectorAuthType
    credentials: dict[str, Any]
    config: dict[str, Any] = Field(default_factory=dict)
    sync_interval_seconds: int | None = Field(default=None, ge=60)


class ConfigureConnectorRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    sync_interval_seconds: int | None = Field(default=None, ge=60)


class StartSyncRequest(APIModel):
    sync_type: SyncType = SyncType.INCREMENTAL
    resume: bool = False


# --- Responses ------------------------------------------------------------


class ConnectorResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    connector_type: str
    name: str
    status: str
    auth_type: str
    config: dict[str, Any]
    health_status: str
    health_checked_at: datetime | None
    health_message: str | None
    sync_interval_seconds: int | None
    last_sync_at: datetime | None
    last_successful_sync_at: datetime | None
    next_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SyncRunResponse(APIModel):
    id: uuid.UUID
    connector_id: uuid.UUID
    sync_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    items_discovered: int
    items_processed: int
    items_skipped: int
    items_failed: int
    cursor: str | None
    error_message: str | None
    triggered_by: uuid.UUID | None
