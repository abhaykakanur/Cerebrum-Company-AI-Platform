"""``DocumentManifest``: the single, stable summary of a
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`'s
Knowledge Preparation outcome — CIS Phase 2 Prompt 4's Document
Manifest. One row per version (overwritten on
:meth:`~cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService.prepare`,
same overwrite-on-rerun convention as
:class:`~cerebrum.infrastructure.database.models.document_extraction.DocumentExtraction`),
giving a future Phase 3 consumer one place to check "is this version's
knowledge ready, and what does it look like" without re-deriving it from
:class:`~cerebrum.infrastructure.database.models.chunk.Chunk` rows every
time.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ManifestStatus(StrEnum):
    READY = "ready"
    FAILED = "failed"


class DocumentManifest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_manifests"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    extraction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_extractions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), index=True)
    chunking_strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    total_character_count: Mapped[int] = mapped_column(Integer, default=0)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    """E.g. ``avg_chunk_size``, ``min_chunk_size``, ``max_chunk_size`` —
    see
    cerebrum.application.knowledge.knowledge_preparation_service.KnowledgePreparationService
    for what populates this.
    """
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
