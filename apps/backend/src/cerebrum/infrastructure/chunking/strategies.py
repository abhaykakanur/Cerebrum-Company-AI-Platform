"""The seven chunking strategies —
:class:`~cerebrum.infrastructure.database.models.chunk.ChunkingStrategy`
— CIS Phase 2 Prompt 4's Chunking Engine. Each strategy is a plain
synchronous callable (offloaded via ``asyncio.to_thread`` at the
service layer — cerebrum.application.knowledge.chunking_service — the
same pattern this codebase already uses for extraction in
cerebrum.application.knowledge.extraction_service), implementing the
:class:`Chunker` Protocol below.

Every returned :class:`~cerebrum.infrastructure.chunking.results.ChunkSpec`
carries real ``start_offset``/``end_offset`` positions into the input
text — never re-derived or approximate — so
``text[start_offset:end_offset] == spec.text`` always holds.
"""

import re
from typing import Protocol

from cerebrum.infrastructure.chunking.options import ChunkingOptions
from cerebrum.infrastructure.chunking.results import ChunkSpec


class Chunker(Protocol):
    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]: ...


class FixedSizeChunker:
    """Consecutive, non-overlapping windows of ``options.chunk_size``
    characters.
    """

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        specs = []
        position = 0
        length = len(text)
        while position < length:
            end = min(position + options.chunk_size, length)
            specs.append(
                ChunkSpec(
                    text=text[position:end], start_offset=position, end_offset=end
                )
            )
            position = end
        return specs


class FixedSizeOverlapChunker:
    """Windows of ``options.chunk_size`` characters, each starting
    ``options.chunk_overlap`` characters before the previous window
    ended.
    """

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        specs: list[ChunkSpec] = []
        length = len(text)
        step = max(options.chunk_size - options.chunk_overlap, 1)
        position = 0
        while position < length:
            end = min(position + options.chunk_size, length)
            overlap = min(options.chunk_overlap, position) if specs else 0
            specs.append(
                ChunkSpec(
                    text=text[position:end],
                    start_offset=position,
                    end_offset=end,
                    overlap_with_previous=overlap,
                )
            )
            if end == length:
                break
            position += step
        return specs


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class SentenceChunker:
    """Groups ``options.sentences_per_chunk`` naive
    (regex-boundary-split) sentences per chunk."""

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        if not text.strip():
            return []
        sentences = [s for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]
        specs = []
        cursor = 0
        group: list[str] = []
        group_start = 0
        for index, sentence in enumerate(sentences):
            start = text.index(sentence, cursor)
            if not group:
                group_start = start
            group.append(sentence)
            cursor = start + len(sentence)
            if len(group) >= options.sentences_per_chunk or index == len(sentences) - 1:
                specs.append(
                    ChunkSpec(
                        text=text[group_start:cursor],
                        start_offset=group_start,
                        end_offset=cursor,
                        metadata={"sentence_count": len(group)},
                    )
                )
                group = []
        return specs


class ParagraphChunker:
    """One chunk per blank-line-delimited paragraph — matches
    cerebrum.infrastructure.extraction.normalize.normalize_text's
    convention of collapsing excess blank lines to exactly one (i.e.
    paragraphs separated by ``"\\n\\n"``).
    """

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        if not text.strip():
            return []
        specs = []
        cursor = 0
        for paragraph in text.split("\n\n"):
            if not paragraph.strip():
                cursor += len(paragraph) + 2
                continue
            start = text.index(paragraph, cursor)
            end = start + len(paragraph)
            specs.append(ChunkSpec(text=paragraph, start_offset=start, end_offset=end))
            cursor = end
        return specs


_RECURSIVE_SEPARATORS = ("\n\n", "\n", ". ", " ")


class RecursiveChunker:
    """Recursively splits on decreasing-granularity separators
    (paragraph, then line, then sentence-ish, then word), merging
    adjacent pieces back together up to ``options.chunk_size`` —
    the well-known "recursive character text splitter" pattern. Falls
    back to a hard character slice only if a single word already
    exceeds ``options.chunk_size``.
    """

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        if not text.strip():
            return []
        pieces = self._split(text, list(_RECURSIVE_SEPARATORS), options.chunk_size)
        specs = []
        cursor = 0
        for piece in pieces:
            if not piece:
                continue
            start = text.index(piece, cursor)
            end = start + len(piece)
            specs.append(ChunkSpec(text=piece, start_offset=start, end_offset=end))
            cursor = end
        return specs

    def _split(self, text: str, separators: list[str], max_size: int) -> list[str]:
        if len(text) <= max_size:
            return [text]
        if not separators:
            return [text[i : i + max_size] for i in range(0, len(text), max_size)]

        separator, remaining_separators = separators[0], separators[1:]
        parts = text.split(separator)
        merged: list[str] = []
        buffer = ""
        for part in parts:
            candidate = buffer + (separator if buffer else "") + part
            if len(candidate) <= max_size:
                buffer = candidate
                continue
            if buffer:
                merged.append(buffer)
            if len(part) <= max_size:
                buffer = part
            else:
                merged.extend(self._split(part, remaining_separators, max_size))
                buffer = ""
        if buffer:
            merged.append(buffer)
        return merged


_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


class HeadingBasedChunker:
    """Splits on Markdown-style ``#``-prefixed heading lines: one chunk
    per section (a heading through the text preceding the next heading
    of any level). A level-2+ heading's chunk points its
    :attr:`~cerebrum.infrastructure.chunking.results.ChunkSpec.parent_index`
    at the nearest preceding level-1 heading's chunk, giving a shallow
    two-level hierarchy — see
    cerebrum.infrastructure.database.models.chunk.Chunk's
    ``parent_chunk_id`` docstring. Text with no headings at all becomes
    one chunk.
    """

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        if not text.strip():
            return []
        matches = list(_HEADING_PATTERN.finditer(text))
        if not matches:
            return [
                ChunkSpec(
                    text=text,
                    start_offset=0,
                    end_offset=len(text),
                    metadata={"heading_text": None, "heading_level": None},
                )
            ]

        specs: list[ChunkSpec] = []
        if matches[0].start() > 0:
            intro = text[: matches[0].start()]
            if intro.strip():
                specs.append(
                    ChunkSpec(
                        text=intro,
                        start_offset=0,
                        end_offset=len(intro),
                        metadata={"heading_text": None, "heading_level": None},
                    )
                )

        last_top_level_index: int | None = None
        for index, match in enumerate(matches):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            parent_index = last_top_level_index if level > 1 else None
            specs.append(
                ChunkSpec(
                    text=text[start:end],
                    start_offset=start,
                    end_offset=end,
                    parent_index=parent_index,
                    metadata={"heading_text": heading_text, "heading_level": level},
                )
            )
            if level == 1:
                last_top_level_index = len(specs) - 1
        return specs


_TOKEN_PATTERN = re.compile(r"\S+\s*")


class FixedTokenCountChunker:
    """Groups ``options.tokens_per_chunk`` whitespace-delimited "tokens"
    per chunk. "Token" here means a whitespace-split word, not a
    subword unit from a real tokenizer (e.g. tiktoken/BPE) — no such
    dependency is added; a real tokenizer-based implementation is a
    drop-in swap of this one class behind the same
    :class:`Chunker` Protocol.
    """

    def chunk(self, text: str, options: ChunkingOptions) -> list[ChunkSpec]:
        if not text.strip():
            return []
        tokens = list(_TOKEN_PATTERN.finditer(text))
        specs = []
        index = 0
        while index < len(tokens):
            group = tokens[index : index + options.tokens_per_chunk]
            start = group[0].start()
            end = group[-1].end()
            specs.append(
                ChunkSpec(
                    text=text[start:end],
                    start_offset=start,
                    end_offset=end,
                    metadata={"token_count": len(group)},
                )
            )
            index += options.tokens_per_chunk
        return specs
