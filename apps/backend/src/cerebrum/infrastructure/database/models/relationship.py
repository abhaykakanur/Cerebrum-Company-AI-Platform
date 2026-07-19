"""``Relationship``: a directed, typed edge between two
:class:`~cerebrum.infrastructure.database.models.entity.Entity` rows —
CIS Phase 3 Prompt 1's Knowledge Graph & Entity Intelligence. Same
"PostgreSQL is the system of record, Neo4j is the synchronized graph
projection" split as ``Entity`` — see that model's docstring.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    AuditFieldsMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UTCDateTime,
    UUIDPrimaryKeyMixin,
)


class RelationshipType(StrEnum):
    """The ten named types CIS Phase 3 Prompt 1 lists, plus ``CUSTOM``
    for a caller-defined type (see ``Relationship.custom_type_name``).
    """

    REFERENCES = "references"
    MENTIONS = "mentions"
    OWNERSHIP = "ownership"
    MEMBERSHIP = "membership"
    DEPENDENCY = "dependency"
    PARENT_CHILD = "parent_child"
    COLLABORATION = "collaboration"
    USES = "uses"
    PRODUCED_BY = "produced_by"
    REPORTS_TO = "reports_to"
    CUSTOM = "custom"


class Relationship(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditFieldsMixin
):
    """No :class:`~cerebrum.infrastructure.database.models.mixins.OptimisticLockMixin`
    — unlike ``Entity`` (whose ``aliases``/``description``/``confidence``
    are actively merged across repeated extractions, making concurrent-
    update races a real concern), a relationship's own fields are only
    ever set once at creation or superseded wholesale by a version-aware
    re-extraction (see ``KnowledgeGraphService``), never merged in place.
    """

    __tablename__ = "relationships"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(30), index=True)
    custom_type_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    """The text snippet an extractor found this relationship's cue
    phrase in — see cerebrum.infrastructure.relationships.extractors.
    """
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    """Temporal metadata CIS Phase 3 Prompt 1 asks for — e.g. a
    ``REPORTS_TO`` relationship extracted from a dated document is only
    known to hold as of that document's date; ``None``/``None`` means
    "no temporal bound is known," not "always true."
    """
