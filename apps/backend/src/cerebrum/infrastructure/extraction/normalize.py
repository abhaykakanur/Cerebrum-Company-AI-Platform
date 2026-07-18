"""The normalization pass every format's extracted text goes through
before storage — CIS Phase 2 Prompt 3's Normalization Pipeline. Each
:class:`~cerebrum.infrastructure.extraction.parsers.TextExtractor`
already returns clean text in its own format's terms (PDF page text,
DOCX paragraph text, ...); this step makes the result consistent
*across* formats, independent of which parser produced it — line-ending
normalization, control-character stripping, and collapsing excess blank
lines, never format-specific interpretation (that stays in
cerebrum.infrastructure.extraction.parsers, one file per format).
"""

import re
import unicodedata

_CONTROL_CHARACTERS = re.compile(
    "[" + "".join(chr(c) for c in range(0x00, 0x20) if c not in (0x09, 0x0A)) + "]"
)
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+$", re.MULTILINE)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _CONTROL_CHARACTERS.sub("", normalized)
    normalized = _TRAILING_WHITESPACE.sub("", normalized)
    normalized = _EXCESS_BLANK_LINES.sub("\n\n", normalized)
    return normalized.strip()
