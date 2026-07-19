"""``CapsuleTimelineEvent``: CIS Phase 5 Prompt 3's Organizational
Timeline — one chronological entry
cerebrum.application.capsules.organizational_memory_service.OrganizationalMemoryService
derives from a
:class:`~cerebrum.infrastructure.database.models.capsule_evidence.CapsuleEvidenceRecord`
(``evidence_record_id`` traces every timeline entry back to the
evidence that justifies it — the same "no unsupported inference"
contract that model's docstring establishes, applied to the timeline).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class CapsuleTimelineEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "capsule_timeline_events"

    capsule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee_knowledge_capsules.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), index=True)
    """One of: ``identity_link``, ``contribution``, ``review``,
    ``ownership_change``, ``incident``, ``decision``, ``deployment``,
    ``project``.
    """
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    evidence_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("capsule_evidence_records.id", ondelete="SET NULL"), nullable=True
    )
