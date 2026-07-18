"""File Foundation (CIS Phase 1 Prompt 6): reusable upload/download/
streaming/validation interfaces a future file-handling feature (Document
Ingestion, Connector attachments, ...) implements against. No document
ingestion, storage-backend selection logic, or business validation rule
lives here — see this milestone's Non-Objectives.

:class:`FileUploader`/:class:`FileDownloader` are Protocol ports, in the
same style as cerebrum.core.observability's ``MetricsRegistry``/``Tracer``
— a concrete adapter (backed by
:class:`~cerebrum.infrastructure.storage.manager.MinIOClientManager`'s
client, per CIS Phase 1 Prompt 4) is Deferred to the first feature that
actually uploads or downloads a file; nothing at this milestone
implements these Protocols yet.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from cerebrum.shared.errors.exceptions import ValidationException


@dataclass(frozen=True, slots=True)
class FileValidationPolicy:
    """What :func:`validate_file` checks a file against. A future feature
    constructs its own policy (e.g. "documents: 100MB max, PDF/DOCX/TXT
    only") rather than this module hard-coding one business rule.
    """

    max_size_bytes: int
    allowed_content_types: frozenset[str] | None = None
    """``None`` means any content type is accepted."""


def validate_file(
    *, filename: str, content_type: str, size_bytes: int, policy: FileValidationPolicy
) -> None:
    """Raises :class:`~cerebrum.shared.errors.exceptions.ValidationException`
    on the first violated rule. Structural validation only (non-empty
    name, non-empty content, size ceiling, allowed content type) — never
    content inspection (e.g. antivirus scanning, magic-byte sniffing),
    which belongs to the feature that actually processes the file.
    """
    if not filename.strip():
        raise ValidationException("File name must not be empty.")
    if size_bytes <= 0:
        raise ValidationException("File is empty.")
    if size_bytes > policy.max_size_bytes:
        raise ValidationException(
            f"File exceeds the {policy.max_size_bytes}-byte limit.",
            context={"size_bytes": size_bytes, "max_size_bytes": policy.max_size_bytes},
        )
    if (
        policy.allowed_content_types is not None
        and content_type not in policy.allowed_content_types
    ):
        raise ValidationException(
            f"Content type '{content_type}' is not permitted.",
            context={
                "content_type": content_type,
                "allowed_content_types": sorted(policy.allowed_content_types),
            },
        )


@dataclass(frozen=True, slots=True)
class UploadedFile:
    """What a :class:`FileUploader` returns on a completed upload — the
    shape an application service works with, independent of the concrete
    storage backend.
    """

    object_key: str
    filename: str
    content_type: str
    size_bytes: int


class FileUploader(Protocol):
    """The Upload port a future MinIO-backed adapter implements."""

    async def upload(
        self,
        *,
        object_key: str,
        content: AsyncIterator[bytes],
        content_type: str,
        size_bytes: int,
    ) -> UploadedFile: ...


class FileDownloader(Protocol):
    """The Download/Streaming port a future MinIO-backed adapter
    implements. Returns an async byte-chunk iterator rather than the full
    file in memory, so a large file can be streamed straight into an
    HTTP response (e.g. FastAPI's ``StreamingResponse``) without
    buffering it server-side.
    """

    async def download(self, *, object_key: str) -> AsyncIterator[bytes]: ...
