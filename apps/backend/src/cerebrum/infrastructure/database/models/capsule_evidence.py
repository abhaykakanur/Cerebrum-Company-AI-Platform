"""``CapsuleEvidenceRecord``: CIS Phase 5 Prompt 3's Evidence Engine —
an append-only ledger entry backing exactly one insight written onto an
:class:`~cerebrum.infrastructure.database.models.capsule.EmployeeKnowledgeCapsule`.
"No unsupported inference": every inference service in
cerebrum.application.capsules creates one of these *before* writing the
corresponding entry into the capsule's JSON maps, and always populates
at least one of ``entity_id``/``relationship_id``/``document_id``/
``connector_id`` — never a bare confidence number with nothing backing
it. No soft delete/audit-fields/optimistic-lock: immutable once
written, the same reasoning
cerebrum.infrastructure.database.models.audit.AuditEvent's docstring
gives for its own append-only shape.
"""

import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class CapsuleEvidenceRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "capsule_evidence_records"

    capsule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee_knowledge_capsules.id", ondelete="CASCADE"), index=True
    )
    insight_type: Mapped[str] = mapped_column(String(30), index=True)
    """One of: ``identity_link``, ``expertise``, ``ownership``,
    ``collaboration``, ``timeline``, ``risk`` — see
    cerebrum.application.capsules.dataclasses for the exact producers.
    """
    insight_key: Mapped[str] = mapped_column(String(500))
    """What the insight is *about* — typically the related entity's
    ``canonical_name``, so evidence for "expertise: Kubernetes" is
    findable without joining back through ``entity_id``.
    """
    confidence: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(2000))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("relationships.id", ondelete="SET NULL"), nullable=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("connectors.id", ondelete="SET NULL"), nullable=True
    )
    external_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
