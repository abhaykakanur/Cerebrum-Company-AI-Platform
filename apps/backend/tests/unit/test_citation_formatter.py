"""Proves CIS Phase 4 Prompt 1's ``CitationFormatter``: stable marker
assignment, human-readable reference lines, and the fallback label for
a citation with no resolved names at all.
"""

import uuid
from typing import Any

import pytest

from cerebrum.application.ai.citation_formatter import CitationFormatter
from cerebrum.application.retrieval.citation_service import EnrichedCitation

pytestmark = pytest.mark.unit


def _citation(**overrides: Any) -> EnrichedCitation:
    defaults: dict[str, Any] = {
        "document_id": uuid.uuid4(),
        "document_version_id": uuid.uuid4(),
        "chunk_id": uuid.uuid4(),
        "entity_id": None,
        "confidence": 0.83,
        "provenance": {},
        "document_name": "Report.pdf",
        "version_number": 2,
        "chunk_index": 5,
        "entity_name": None,
    }
    defaults.update(overrides)
    return EnrichedCitation(**defaults)


def test_marker_is_one_indexed_bracketed() -> None:
    assert CitationFormatter.marker(1) == "[1]"
    assert CitationFormatter.marker(2) == "[2]"


def test_assign_markers_preserves_order() -> None:
    citations = [_citation(), _citation()]

    markers = CitationFormatter.assign_markers(citations)

    assert list(markers.keys()) == ["[1]", "[2]"]
    assert markers["[1]"] is citations[0]
    assert markers["[2]"] is citations[1]


def test_label_includes_document_version_and_chunk() -> None:
    citation = _citation(document_name="Handbook.pdf", version_number=3, chunk_index=7)

    label = CitationFormatter.label(citation)

    assert "Handbook.pdf" in label
    assert "version 3" in label
    assert "chunk 7" in label
    assert "0.83" in label


def test_label_includes_entity_name_when_present() -> None:
    citation = _citation(
        document_name=None, version_number=None, chunk_index=None, entity_name="Acme"
    )

    label = CitationFormatter.label(citation)

    assert "entity: Acme" in label


def test_label_falls_back_when_nothing_resolved() -> None:
    citation = _citation(
        document_name=None, version_number=None, chunk_index=None, entity_name=None
    )

    label = CitationFormatter.label(citation)

    assert "unattributed source" in label


def test_format_reference_line_prefixes_marker() -> None:
    citation = _citation(document_name="Report.pdf")

    line = CitationFormatter.format_reference_line("[1]", citation)

    assert line.startswith("[1] ")
    assert "Report.pdf" in line
