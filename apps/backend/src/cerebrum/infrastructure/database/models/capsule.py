"""``EmployeeKnowledgeCapsule``: CIS Phase 5 Prompt 3's Digital
Organizational Twin — a materialized, workspace-scoped synthesis of one
employee's role, expertise, ownership, collaboration network, and
technical leadership. Holds the *current cached view*; every value on
it is only ever written by
cerebrum.application.capsules.employee_knowledge_capsule_service.EmployeeKnowledgeCapsuleService.refresh
from evidence recorded in
:class:`~cerebrum.infrastructure.database.models.capsule_evidence.CapsuleEvidenceRecord`
rows — never asserted directly, mirroring the "no unsupported
inference" requirement structurally rather than by convention alone.

``person_entity_id`` is nullable: a capsule exists (so it can be
addressed/refreshed-into) before an operator has confirmed which
knowledge-graph :class:`~cerebrum.infrastructure.database.models.entity.Entity`
row (of ``entity_type=PERSON``) actually corresponds to this employee —
see that service's ``link_person_entity``. Automatic name-matching
between extracted entities and identity is deliberately not attempted
(the extractor's own docstring calls its PERSON regex unreliable) — an
unverified identity link would make every downstream insight
unsupported inference by construction.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class EmployeeKnowledgeCapsule(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditFieldsMixin,
    OptimisticLockMixin,
):
    __tablename__ = "employee_knowledge_capsules"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    person_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )
    organizational_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    expertise_map: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    ownership_map: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    active_projects: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    collaboration_network: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list
    )
    technical_leadership: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list
    )
    capsule_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_stale: Mapped[bool] = mapped_column(default=True, index=True)
    stale_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
