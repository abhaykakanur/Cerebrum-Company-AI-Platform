"""``AuditService``: records the seven security audit event types CIS
Phase 1 Prompt 5 names. Audit events only — no analytics (this service
never aggregates, queries trends, or computes anything from the events
it records; see cerebrum.infrastructure.database.models.audit's
docstring).
"""

import uuid
from typing import Any

from cerebrum.infrastructure.database.models.audit import AuditEvent, AuditEventType
from cerebrum.repositories.base import AbstractRepository


class AuditService:
    def __init__(
        self, audit_repository: AbstractRepository[AuditEvent, uuid.UUID]
    ) -> None:
        self._audit_repository = audit_repository

    async def record(
        self,
        event_type: AuditEventType,
        *,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            event_type=event_type.value,
            user_id=user_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            ip_address=ip_address,
            event_metadata=metadata or {},
        )
        await self._audit_repository.add(event)
