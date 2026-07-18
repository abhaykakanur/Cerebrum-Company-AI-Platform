"""Proves each of CIS Phase 2 Prompt 4's seven chunking strategies:
every returned ``ChunkSpec``'s offsets must round-trip
(``text[start:end] == spec.text``), and each strategy's own distinctive
behavior (overlap, sentence/paragraph grouping, the recursive size
ceiling, heading parent/child linkage, approximate token grouping).
"""

import pytest

from cerebrum.infrastructure.chunking.options import ChunkingOptions
from cerebrum.infrastructure.chunking.strategies import (
    FixedSizeChunker,
    FixedSizeOverlapChunker,
    FixedTokenCountChunker,
    HeadingBasedChunker,
    ParagraphChunker,
    RecursiveChunker,
    SentenceChunker,
)

pytestmark = pytest.mark.unit


def _assert_offsets_round_trip(text: str, specs: list) -> None:
    for spec in specs:
        assert text[spec.start_offset : spec.end_offset] == spec.text


def test_fixed_size_chunker_splits_into_equal_windows() -> None:
    text = "a" * 250
    specs = FixedSizeChunker().chunk(text, ChunkingOptions(chunk_size=100))

    assert [len(s.text) for s in specs] == [100, 100, 50]
    _assert_offsets_round_trip(text, specs)


def test_fixed_size_chunker_handles_empty_text() -> None:
    assert FixedSizeChunker().chunk("", ChunkingOptions()) == []


def test_fixed_size_overlap_chunker_overlaps_consecutive_windows() -> None:
    text = "a" * 250
    specs = FixedSizeOverlapChunker().chunk(
        text, ChunkingOptions(chunk_size=100, chunk_overlap=20)
    )

    _assert_offsets_round_trip(text, specs)
    assert specs[0].overlap_with_previous == 0
    assert all(s.overlap_with_previous == 20 for s in specs[1:])
    assert specs[1].start_offset == specs[0].end_offset - 20


def test_sentence_chunker_groups_sentences() -> None:
    text = "One. Two! Three? Four. Five."
    specs = SentenceChunker().chunk(text, ChunkingOptions(sentences_per_chunk=2))

    _assert_offsets_round_trip(text, specs)
    assert [s.metadata["sentence_count"] for s in specs] == [2, 2, 1]


def test_paragraph_chunker_splits_on_blank_lines() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird."
    specs = ParagraphChunker().chunk(text, ChunkingOptions())

    assert [s.text for s in specs] == [
        "First paragraph.",
        "Second paragraph.",
        "Third.",
    ]
    _assert_offsets_round_trip(text, specs)


def test_recursive_chunker_respects_the_size_ceiling() -> None:
    text = ("Sentence one. " * 5) + "\n\n" + ("Sentence two. " * 5)
    specs = RecursiveChunker().chunk(text, ChunkingOptions(chunk_size=60))

    assert all(len(s.text) <= 60 for s in specs)
    _assert_offsets_round_trip(text, specs)


def test_recursive_chunker_falls_back_to_hard_slicing_for_one_giant_word() -> None:
    text = "x" * 500
    specs = RecursiveChunker().chunk(text, ChunkingOptions(chunk_size=100))

    assert all(len(s.text) <= 100 for s in specs)
    _assert_offsets_round_trip(text, specs)


def test_heading_based_chunker_links_sub_headings_to_their_parent() -> None:
    text = (
        "# Title\nIntro.\n## Sub A\nContent A.\n## Sub B\nContent B.\n# Title2\nMore."
    )
    specs = HeadingBasedChunker().chunk(text, ChunkingOptions())

    _assert_offsets_round_trip(text, specs)
    headings = [(s.metadata["heading_text"], s.parent_index) for s in specs]
    assert headings == [
        ("Title", None),
        ("Sub A", 0),
        ("Sub B", 0),
        ("Title2", None),
    ]


def test_heading_based_chunker_falls_back_to_one_chunk_with_no_headings() -> None:
    text = "Just plain text, no markdown headings at all."
    specs = HeadingBasedChunker().chunk(text, ChunkingOptions())

    assert len(specs) == 1
    assert specs[0].text == text
    assert specs[0].metadata == {"heading_text": None, "heading_level": None}


def test_fixed_token_count_chunker_groups_whitespace_tokens() -> None:
    text = "one two three four five six"
    specs = FixedTokenCountChunker().chunk(text, ChunkingOptions(tokens_per_chunk=2))

    _assert_offsets_round_trip(text, specs)
    assert [s.metadata["token_count"] for s in specs] == [2, 2, 2]
    assert "".join(s.text for s in specs) == text


@pytest.mark.parametrize(
    "chunker_cls",
    [
        FixedSizeChunker,
        FixedSizeOverlapChunker,
        SentenceChunker,
        ParagraphChunker,
        RecursiveChunker,
        HeadingBasedChunker,
        FixedTokenCountChunker,
    ],
)
def test_every_strategy_returns_no_chunks_for_empty_text(chunker_cls: type) -> None:
    assert chunker_cls().chunk("", ChunkingOptions()) == []
