"""Maps a
:class:`~cerebrum.infrastructure.database.models.chunk.ChunkingStrategy`
to the :class:`~cerebrum.infrastructure.chunking.strategies.Chunker`
that implements it — CIS Phase 2 Prompt 4's strategy dispatch.
"""

from cerebrum.infrastructure.chunking.strategies import (
    Chunker,
    FixedSizeChunker,
    FixedSizeOverlapChunker,
    FixedTokenCountChunker,
    HeadingBasedChunker,
    ParagraphChunker,
    RecursiveChunker,
    SentenceChunker,
)
from cerebrum.infrastructure.database.models.chunk import ChunkingStrategy


def build_chunker_registry() -> dict[ChunkingStrategy, Chunker]:
    return {
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunker(),
        ChunkingStrategy.FIXED_SIZE_OVERLAP: FixedSizeOverlapChunker(),
        ChunkingStrategy.SENTENCE: SentenceChunker(),
        ChunkingStrategy.PARAGRAPH: ParagraphChunker(),
        ChunkingStrategy.RECURSIVE: RecursiveChunker(),
        ChunkingStrategy.HEADING_BASED: HeadingBasedChunker(),
        ChunkingStrategy.FIXED_TOKEN_COUNT: FixedTokenCountChunker(),
    }
