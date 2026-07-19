"""The shape every entity extractor returns — independent of which
extractor produced it."""

from dataclasses import dataclass

from cerebrum.infrastructure.database.models.entity import EntityType


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    entity_type: EntityType
    canonical_name: str
    confidence: float
    context: str
    """The surrounding text the mention was found in — becomes the
    first entry in the persisted
    :attr:`~cerebrum.infrastructure.database.models.entity.Entity.provenance`
    record, and the input
    cerebrum.infrastructure.relationships.extractors scans for cue
    phrases between co-occurring entities.
    """
    start_offset: int
    end_offset: int
    custom_type_name: str | None = None
