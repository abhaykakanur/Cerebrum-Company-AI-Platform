"""Virus Scan abstraction — CIS Phase 2 Prompt 2's Security requirement.
Same Protocol-plus-NoOp shape as
:class:`~cerebrum.core.observability.MetricsRegistry`/``Tracer`` and
:class:`~cerebrum.infrastructure.storage.files.FileUploader`/``FileDownloader``:
the port is defined and wired into the upload pipeline now; no real
antivirus engine (e.g. ClamAV) integration exists yet — Deferred to the
first deployment that actually needs one. Every upload is scanned
through this port regardless, so wiring a real scanner later requires
no change to
cerebrum.application.knowledge.upload_service.UploadService, only a new
class satisfying this same Protocol.
"""

from dataclasses import dataclass
from typing import Protocol

from cerebrum.infrastructure.database.models.document_metadata import (
    QuarantineStatus,
)


@dataclass(frozen=True, slots=True)
class ScanResult:
    status: QuarantineStatus
    detail: str | None = None


class VirusScanner(Protocol):
    async def scan(self, content: bytes) -> ScanResult: ...


class NoOpVirusScanner:
    """Always reports ``CLEAN`` — see this module's docstring. Never
    reports ``QUARANTINED``; a real scanner is what makes that outcome
    reachable.
    """

    async def scan(self, content: bytes) -> ScanResult:
        return ScanResult(status=QuarantineStatus.CLEAN)
