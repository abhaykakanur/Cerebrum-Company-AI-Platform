"""``ConnectorService``: CIS Phase 5 Prompt 1's Connector Registry,
Connector Configuration, Connector Lifecycle, Connector Health, and
Connector Validation — CRUD/lifecycle over
:class:`~cerebrum.infrastructure.database.models.connector.Connector`,
mirroring
cerebrum.application.knowledge.document_service.DocumentService's exact
shape (create/get/rename-ish-configure/change_status/soft_delete/list_in_workspace).

**Secret Isolation** (CIS Phase 5 Prompt 1's Security requirement):
:attr:`~cerebrum.infrastructure.database.models.connector.Connector.credentials`
is never included in this service's return values in a form meant for
API serialization — see cerebrum.api.schemas.connector's docstring for
where that boundary is actually enforced (a response schema that simply
never declares a ``credentials`` field). :meth:`get_credentials` is the
one method that decrypts/returns them, and it always records a
``CONNECTOR_CREDENTIALS_ACCESSED`` audit event — CIS Phase 5 Prompt 1's
Audit Logging requirement, applied to the one operation in this whole
feature that actually touches a secret.
"""

import uuid
from datetime import timedelta
from types import EllipsisType
from typing import Any

import httpx

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.connectors.events import (
    ConnectorHealthyEvent,
    ConnectorRegisteredEvent,
    ConnectorUnhealthyEvent,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.connectors.base import (
    ConnectorCredentials,
    ConnectorError,
    credentials_from_raw,
)
from cerebrum.infrastructure.connectors.registry import build_connector
from cerebrum.infrastructure.connectors.validation import validate_connector_setup
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.connector import (
    Connector,
    ConnectorAuthType,
    ConnectorHealthStatus,
    ConnectorStatus,
    ConnectorType,
)
from cerebrum.repositories.contracts import FilterOperator, FilterSpec, Page, Pagination
from cerebrum.repositories.postgres.connector_repository import ConnectorRepository
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException
from cerebrum.utils.clock import utcnow

_NAME_MAX_LENGTH = 255


class ConnectorService:
    def __init__(
        self,
        *,
        connector_repository: ConnectorRepository,
        event_dispatcher: EventDispatcher,
        audit_service: AuditService,
    ) -> None:
        self._connectors = connector_repository
        self._events = event_dispatcher
        self._audit = audit_service

    async def register(
        self,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        connector_type: ConnectorType,
        name: str,
        auth_type: ConnectorAuthType,
        credentials: dict[str, Any],
        config: dict[str, Any],
        created_by: uuid.UUID,
        sync_interval_seconds: int | None = None,
    ) -> Connector:
        errors = validate_connector_setup(
            connector_type=connector_type, config=config, credentials=credentials
        )
        if errors:
            raise ValidationException(
                "Connector configuration is incomplete.",
                context={"errors": errors},
            )

        connector = Connector(
            workspace_id=workspace_id,
            organization_id=organization_id,
            connector_type=connector_type.value,
            name=name[:_NAME_MAX_LENGTH],
            status=ConnectorStatus.ACTIVE.value,
            auth_type=auth_type.value,
            credentials=credentials,
            config=config,
            health_status=ConnectorHealthStatus.UNKNOWN.value,
            sync_interval_seconds=sync_interval_seconds,
            next_sync_at=utcnow() if sync_interval_seconds else None,
            created_by=created_by,
            updated_by=created_by,
        )
        created = await self._connectors.add(connector)

        await self._audit.record(
            AuditEventType.CONNECTOR_REGISTERED,
            user_id=created_by,
            workspace_id=workspace_id,
            organization_id=organization_id,
            metadata={
                "connector_id": str(created.id),
                "connector_type": connector_type.value,
            },
        )
        self._events.publish(
            ConnectorRegisteredEvent(
                connector_id=created.id,
                workspace_id=workspace_id,
                connector_type=connector_type.value,
            )
        )
        return created

    async def get(
        self, connector_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Connector:
        connector = await self._connectors.get_by_id(connector_id)
        if connector is None or connector.workspace_id != workspace_id:
            raise NotFoundException(f"No connector with id {connector_id}.")
        return connector

    async def configure(
        self,
        connector_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        updated_by: uuid.UUID,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        sync_interval_seconds: int | None | EllipsisType = ...,
    ) -> Connector:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        if name is not None:
            connector.name = name[:_NAME_MAX_LENGTH]
        if config is not None:
            connector.config = config
        if credentials is not None:
            connector.credentials = credentials
        if not isinstance(sync_interval_seconds, EllipsisType):
            connector.sync_interval_seconds = sync_interval_seconds
            connector.next_sync_at = utcnow() if sync_interval_seconds else None

        errors = validate_connector_setup(
            connector_type=ConnectorType(connector.connector_type),
            config=connector.config,
            credentials=connector.credentials,
        )
        if errors:
            raise ValidationException(
                "Connector configuration is incomplete.",
                context={"errors": errors},
            )

        connector.updated_by = updated_by
        updated = await self._connectors.update(connector)
        await self._audit.record(
            AuditEventType.CONNECTOR_CONFIGURED,
            user_id=updated_by,
            workspace_id=workspace_id,
            metadata={"connector_id": str(connector_id)},
        )
        return updated

    async def change_status(
        self,
        connector_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        status: ConnectorStatus,
        updated_by: uuid.UUID,
    ) -> Connector:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        connector.status = status.value
        connector.updated_by = updated_by
        return await self._connectors.update(connector)

    async def delete(
        self, connector_id: uuid.UUID, *, workspace_id: uuid.UUID, deleted_by: uuid.UUID
    ) -> None:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        connector.status = ConnectorStatus.DISABLED.value
        connector.updated_by = deleted_by
        await self._connectors.update(connector)
        await self._connectors.soft_delete(connector_id)
        await self._audit.record(
            AuditEventType.CONNECTOR_DELETED,
            user_id=deleted_by,
            workspace_id=workspace_id,
            metadata={"connector_id": str(connector_id)},
        )

    async def list_in_workspace(
        self,
        *,
        workspace_id: uuid.UUID,
        pagination: Pagination,
        status: ConnectorStatus | None = None,
        connector_type: ConnectorType | None = None,
    ) -> Page[Connector]:
        filters = [
            FilterSpec(
                field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
            )
        ]
        if status is not None:
            filters.append(
                FilterSpec(
                    field="status", operator=FilterOperator.EQ, value=status.value
                )
            )
        if connector_type is not None:
            filters.append(
                FilterSpec(
                    field="connector_type",
                    operator=FilterOperator.EQ,
                    value=connector_type.value,
                )
            )
        return await self._connectors.list(pagination=pagination, filters=filters)

    async def record_sync_success(
        self, connector_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Connector:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        now = utcnow()
        connector.last_sync_at = now
        connector.last_successful_sync_at = now
        connector.status = ConnectorStatus.ACTIVE.value
        if connector.sync_interval_seconds:
            connector.next_sync_at = now + timedelta(
                seconds=connector.sync_interval_seconds
            )
        return await self._connectors.update(connector)

    async def record_sync_failure(
        self, connector_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> Connector:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        connector.last_sync_at = utcnow()
        connector.status = ConnectorStatus.ERROR.value
        return await self._connectors.update(connector)

    async def get_credentials(
        self,
        connector_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        accessed_by: uuid.UUID | None,
    ) -> ConnectorCredentials:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        await self._audit.record(
            AuditEventType.CONNECTOR_CREDENTIALS_ACCESSED,
            user_id=accessed_by,
            workspace_id=workspace_id,
            metadata={"connector_id": str(connector_id)},
        )
        return credentials_from_raw(
            auth_type=ConnectorAuthType(connector.auth_type),
            raw=connector.credentials,
        )

    async def check_health(
        self,
        connector_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        http_client: httpx.AsyncClient,
        checked_by: uuid.UUID | None = None,
    ) -> Connector:
        connector = await self.get(connector_id, workspace_id=workspace_id)
        credentials = await self.get_credentials(
            connector_id, workspace_id=workspace_id, accessed_by=checked_by
        )
        adapter = build_connector(
            ConnectorType(connector.connector_type), http_client=http_client
        )
        try:
            await adapter.test_connection(
                credentials=credentials, config=connector.config
            )
        except ConnectorError as exc:
            connector.health_status = ConnectorHealthStatus.UNHEALTHY.value
            connector.health_message = str(exc)
            connector.health_checked_at = utcnow()
            updated = await self._connectors.update(connector)
            self._events.publish(
                ConnectorUnhealthyEvent(
                    connector_id=connector_id,
                    workspace_id=workspace_id,
                    message=str(exc),
                )
            )
            return updated

        connector.health_status = ConnectorHealthStatus.HEALTHY.value
        connector.health_message = None
        connector.health_checked_at = utcnow()
        updated = await self._connectors.update(connector)
        self._events.publish(
            ConnectorHealthyEvent(connector_id=connector_id, workspace_id=workspace_id)
        )
        return updated
