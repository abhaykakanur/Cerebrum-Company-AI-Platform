"""``ProcessingJob``: a queued unit of future background work against one
:class:`~cerebrum.infrastructure.database.models.document_version.DocumentVersion`
— CIS Phase 2 Prompt 2's Background Processing framework. Records that a
job of a given type was requested and tracks its status/progress/retry
state; no job type's actual handler (OCR, parsing, chunking, embeddings)
is implemented anywhere in this codebase yet — see
cerebrum.workers.queue's docstring for the same "interface/framework,
not the work itself" scope, and this milestone's explicit "Prepare jobs
... Do not implement them."
"""

import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cerebrum.infrastructure.database.base import Base
from cerebrum.infrastructure.database.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ProcessingJobType(StrEnum):
    """The four future pipeline stages CIS Phase 2 Prompt 2 names
    explicitly. No handler exists for any of them yet.
    """

    OCR = "ocr"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDINGS = "embeddings"


class ProcessingJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "processing_jobs"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), index=True
    )
    job_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ProcessingJobStatus.PENDING.value, index=True
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
