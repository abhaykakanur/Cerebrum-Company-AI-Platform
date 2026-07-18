"""``Chunk``: one segment of a
:class:`~cerebrum.infrastructure.database.models.document_extraction.DocumentExtraction`'s
normalized text — CIS Phase 2 Prompt 4's Chunking Engine. Many rows per
version (unlike the 1:1 ``DocumentExtraction``/``DocumentMetadata``
tables); re-chunking a version (a new
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
of type ``CHUNKING``) replaces its prior chunk set rather than
accumulating multiple generations — see
cerebrum.application.knowledge.chunking_service.ChunkingService.

No embeddings, no vector IDs, no Knowledge Graph linkage here — this
table stores chunk text/position/relationships only; see this
milestone's Non-Objectives.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ChunkingStrategy(StrEnum):
    """The seven chunking strategies CIS Phase 2 Prompt 4 names — see
    cerebrum.infrastructure.chunking.strategies for each one's
    implementation.
    """

    FIXED_SIZE = "fixed_size"
    FIXED_SIZE_OVERLAP = "fixed_size_overlap"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    RECURSIVE = "recursive"
    HEADING_BASED = "heading_based"
    FIXED_TOKEN_COUNT = "fixed_token_count"


class Chunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chunks"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_extractions.id", ondelete="CASCADE"), index=True
    )
    processing_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True
    )
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    """Populated only by :data:`ChunkingStrategy.HEADING_BASED` — a
    sub-section chunk points at the heading chunk it falls under, giving
    a shallow two-level hierarchy. ``None`` for every other strategy.
    """
    strategy: Mapped[str] = mapped_column(String(30), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    """0-based order within this version's chunk set — the sequence a
    reader (or a future Phase 3 embedding pipeline) should process
    chunks in, independent of any ``parent_chunk_id`` hierarchy.
    """
    text: Mapped[str] = mapped_column(Text)
    character_count: Mapped[int] = mapped_column(Integer)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    """Character offsets into the owning
    :class:`~cerebrum.infrastructure.database.models.document_extraction.DocumentExtraction`'s
    ``extracted_text`` — ``text == extracted_text[start_offset:end_offset]``
    for every non-overlapping strategy; overlapping strategies (see
    :data:`ChunkingStrategy.FIXED_SIZE_OVERLAP`) may have
    ``start_offset`` earlier than the previous chunk's ``end_offset``.
    """
    overlap_with_previous: Mapped[int] = mapped_column(Integer, default=0)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    """Strategy-specific extras — e.g. ``heading_text`` for
    ``HEADING_BASED``, ``sentence_count`` for ``SENTENCE``. See
    cerebrum.infrastructure.chunking.strategies for what each strategy
    populates.
    """
