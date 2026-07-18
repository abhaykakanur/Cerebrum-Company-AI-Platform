"""Tunable parameters every chunking strategy reads a subset of — one
shared options type rather than a different signature per strategy, so
cerebrum.application.knowledge.chunking_service.ChunkingService can call
any strategy identically.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingOptions:
    chunk_size: int = 1000
    """Max characters per chunk — read by ``FIXED_SIZE``,
    ``FIXED_SIZE_OVERLAP``, and as the size ceiling ``RECURSIVE`` splits
    down to.
    """
    chunk_overlap: int = 100
    """Characters of overlap between consecutive chunks — read by
    ``FIXED_SIZE_OVERLAP`` only.
    """
    sentences_per_chunk: int = 5
    """Read by ``SENTENCE`` only."""
    tokens_per_chunk: int = 200
    """Read by ``FIXED_TOKEN_COUNT`` only — see
    cerebrum.infrastructure.chunking.strategies.FixedTokenCountChunker's
    docstring for what "token" means here.
    """
