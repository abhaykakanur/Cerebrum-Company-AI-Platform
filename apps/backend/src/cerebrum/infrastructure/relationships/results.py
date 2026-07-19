"""The shape every relationship extractor returns — independent of
which extractor produced it."""

from dataclasses import dataclass

from cerebrum.infrastructure.database.models.relationship import RelationshipType


@dataclass(frozen=True, slots=True)
class ExtractedRelationship:
    source_index: int
    """Index into the ``entities`` list passed to
    :meth:`~cerebrum.infrastructure.relationships.extractors.RelationshipExtractor.extract`
    — not a database ID; the caller (``RelationshipService``) resolves
    this to a real ``Entity.id`` once every entity in the batch has one,
    the same convention
    cerebrum.infrastructure.chunking.results.ChunkSpec.parent_index
    already established.
    """
    target_index: int
    relationship_type: RelationshipType
    confidence: float
    evidence: str
    custom_type_name: str | None = None
