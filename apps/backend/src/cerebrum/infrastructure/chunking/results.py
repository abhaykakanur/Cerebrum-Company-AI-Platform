"""The shape every chunking strategy returns — independent of which
strategy produced it."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ChunkSpec:
    text: str
    start_offset: int
    end_offset: int
    overlap_with_previous: int = 0
    parent_index: int | None = None
    """Index into the same strategy call's returned list — e.g.
    :data:`~cerebrum.infrastructure.database.models.chunk.ChunkingStrategy.HEADING_BASED`'s
    sub-heading chunks point back at their section's heading chunk. Not
    a database ID: cerebrum.application.knowledge.chunking_service.ChunkingService
    resolves this to a real ``Chunk.id`` after insertion, once every
    chunk in the batch has one.
    """
    metadata: dict[str, Any] = field(default_factory=dict)
