"""``DocumentExtraction``: the extracted-text-and-metadata result of
running CIS Phase 2 Prompt 3's Intelligent Document Processing Pipeline
against one
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`.

One row per version (``document_version_id`` is unique) — re-extraction
(CIS Phase 2 Prompt 2's Retry, applied to a ``PARSING``/``OCR``
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`)
overwrites this row rather than accumulating a history table; the job's
own retry/status/progress history already lives on
:class:`~cerebrum.infrastructure.database.models.processing_job.ProcessingJob`
(and its ``ProcessingJobRepository.list_by_document_version`` gives the
per-version job history CIS Phase 2 Prompt 2's History endpoint
exposes), so duplicating that trail here would be redundant.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ExtractionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    UNSUPPORTED_FORMAT = "unsupported_format"


class DocumentExtraction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_extractions"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    processing_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    """Format-specific fields a parser recovers — e.g. ``page_count``,
    ``word_count``, ``author``, ``title``, ``sheet_names`` — see
    cerebrum.infrastructure.extraction.parsers for what each format's
    extractor populates. Deliberately schemaless (``JSON``, not a fixed
    column per field): every format surfaces a different set of
    attributes, and a fixed column set would either force every parser
    into an ill-fitting shape or need a migration per new format.
    """
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
