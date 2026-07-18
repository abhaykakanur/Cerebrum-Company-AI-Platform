"""The shape every format extractor returns — independent of which
parsing library produced it."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
