"""Maps a MIME type to the
:class:`~cerebrum.infrastructure.extraction.parsers.TextExtractor` that
handles it — CIS Phase 2 Prompt 3's format dispatch. Supporting a new
format means adding one entry here plus one ``TextExtractor``
implementation in cerebrum.infrastructure.extraction.parsers; nothing in
cerebrum.application.knowledge.extraction_service changes.
"""

from cerebrum.infrastructure.extraction.ocr import NoOpOCREngine, OCREngine
from cerebrum.infrastructure.extraction.parsers import (
    CsvExtractor,
    DocxExtractor,
    EmailExtractor,
    HtmlExtractor,
    ImageExtractor,
    PdfExtractor,
    PlainTextExtractor,
    PptxExtractor,
    TextExtractor,
    XlsxExtractor,
)

_IMAGE_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
)


def build_extractor_registry(
    ocr_engine: OCREngine | None = None,
) -> dict[str, TextExtractor]:
    registry: dict[str, TextExtractor] = {
        "text/plain": PlainTextExtractor(),
        "text/markdown": PlainTextExtractor(),
        "text/html": HtmlExtractor(),
        "text/csv": CsvExtractor(),
        "application/pdf": PdfExtractor(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
            DocxExtractor()
        ),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
            PptxExtractor()
        ),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
            XlsxExtractor()
        ),
        "message/rfc822": EmailExtractor(),
    }
    image_extractor = ImageExtractor(ocr_engine or NoOpOCREngine())
    for mime_type in _IMAGE_MIME_TYPES:
        registry[mime_type] = image_extractor
    return registry
