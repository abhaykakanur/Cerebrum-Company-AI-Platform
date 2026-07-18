"""OCR abstraction — the same Protocol + NoOp port pattern
cerebrum.infrastructure.security.virus_scan established for a
sandbox-unavailable piece of infrastructure: a real OCR engine
(Tesseract via ``pytesseract``, a cloud OCR API) needs a system binary
or network dependency this environment cannot guarantee, so
:class:`NoOpOCREngine` — always "no text recognized" — is the only
implementation wired up here. A future
:class:`~cerebrum.infrastructure.extraction.parsers.ImageExtractor` caller
supplies a real :class:`OCREngine` without this Protocol or
``ImageExtractor`` itself changing.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OCRResult:
    text: str


class OCREngine(Protocol):
    def recognize(self, image_bytes: bytes) -> OCRResult: ...


class NoOpOCREngine:
    def recognize(self, image_bytes: bytes) -> OCRResult:
        return OCRResult(text="")
