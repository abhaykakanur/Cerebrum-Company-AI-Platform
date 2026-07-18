"""Proves CIS Phase 2 Prompt 3's Normalization Pipeline: consistent
line endings, no control characters, no excess blank lines, regardless
of which format's extractor produced the raw text.
"""

import pytest

from cerebrum.infrastructure.extraction.normalize import normalize_text

pytestmark = pytest.mark.unit


def test_normalizes_crlf_and_cr_line_endings_to_lf() -> None:
    assert normalize_text("line one\r\nline two\rline three") == (
        "line one\nline two\nline three"
    )


def test_strips_control_characters_but_keeps_tabs_and_newlines() -> None:
    text = "hello\x00\x07world\tindented\n"
    assert normalize_text(text) == "helloworld\tindented"


def test_collapses_three_or_more_blank_lines_to_two() -> None:
    text = "first\n\n\n\n\nsecond"
    assert normalize_text(text) == "first\n\nsecond"


def test_strips_trailing_whitespace_per_line_and_overall() -> None:
    text = "  line with trailing spaces   \nanother line\t\n  \n"
    assert normalize_text(text) == "line with trailing spaces\nanother line"
