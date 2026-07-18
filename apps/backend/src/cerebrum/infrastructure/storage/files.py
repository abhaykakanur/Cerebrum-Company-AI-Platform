"""File Foundation (CIS Phase 1 Prompt 6, implemented by CIS Phase 2
Prompt 2's Document Upload & Ingestion Pipeline): reusable upload/
download/streaming/validation interfaces a file-handling feature
implements against. No document ingestion (parsing, OCR, chunking)
lives here — see this milestone's Non-Objectives.

:class:`FileUploader`/:class:`FileDownloader` are Protocol ports, in the
same style as cerebrum.core.observability's ``MetricsRegistry``/``Tracer``.
:class:`~cerebrum.infrastructure.storage.minio_files.MinIOFileUploader`/
``MinIOFileDownloader`` are the first concrete adapters (CIS Phase 2
Prompt 2) — ``delete``/presigned-URL methods were added to these
Protocols alongside that implementation, since Phase 1 Prompt 6 only
speculatively named "Upload, Download, Streaming, Validation" without
committing to the full method set a real adapter needs.
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
    """The Upload port a MinIO-backed adapter implements.

    ``content: bytes``, not an ``AsyncIterator[bytes]``: CIS Phase 2
    Prompt 2's upload pipeline
    (cerebrum.application.knowledge.upload_service.UploadService) must
    compute the SHA256 checksum of the *complete* content and enforce
    the configured size ceiling before committing to a store, so it
    already holds the whole upload in memory (bounded by that same size
    ceiling, checked progressively while reading — see that service's
    docstring) by the time this is called. A true end-to-end chunked
    stream (client -> this port -> MinIO, hashing incrementally) is a
    documented future optimization, not a change to this contract's
    callers.
    """

    async def upload(
        self,
        *,
        object_key: str,
        content: bytes,
        content_type: str,
        size_bytes: int,
    ) -> UploadedFile: ...

    async def delete(self, object_key: str) -> None: ...

    async def presigned_upload_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str: ...


class FileDownloader(Protocol):
    """The Download/Streaming port a MinIO-backed adapter implements.
    Returns an async byte-chunk iterator so a route can hand it straight
    to FastAPI's ``StreamingResponse``.

    ``download`` is declared *without* ``async`` deliberately, per
    mypy's own guidance for typing an async-generator method on a
    Protocol: calling it must synchronously return the
    ``AsyncIterator[bytes]`` itself (for ``async for chunk in
    downloader.download(...)``), not a coroutine that must first be
    awaited to *obtain* the iterator — an implementation satisfies this
    by being an async generator function (``async def ... yield ...``),
    exactly as ``async def`` + ``yield`` already behaves in Python.
    """

    def download(self, *, object_key: str) -> AsyncIterator[bytes]: ...

    async def presigned_download_url(
        self, object_key: str, *, expires_in_seconds: int = 3600
    ) -> str: ...
