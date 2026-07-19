"""Canonical entity resolution — CIS Phase 3 Prompt 1's Deduplication.
Exact match and alias matching are deterministic; the configurable
similarity threshold falls back to ``difflib.SequenceMatcher`` (stdlib,
no embeddings — see this milestone's "DO NOT IMPLEMENT: Embeddings"
boundary). Used by
cerebrum.application.knowledge_graph.entity_service.EntityService.upsert_from_extraction
to decide whether a freshly-extracted entity is the same real-world
thing as one already persisted (duplicate prevention) or genuinely new.
"""

from difflib import SequenceMatcher

from cerebrum.infrastructure.database.models.entity import Entity
from cerebrum.infrastructure.entities.results import ExtractedEntity

DEFAULT_SIMILARITY_THRESHOLD = 0.85


def find_duplicate(
    candidate: ExtractedEntity,
    existing_entities: list[Entity],
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Entity | None:
    """``existing_entities`` is expected to already be scoped to the
    same workspace and entity type (see
    cerebrum.repositories.postgres.entity_repository.EntityRepository.list_by_workspace_and_type)
    — this function does no scoping of its own, only matching.
    """
    target = candidate.canonical_name.strip().casefold()

    for existing in existing_entities:
        if existing.canonical_name.strip().casefold() == target:
            return existing
        if any(alias.strip().casefold() == target for alias in existing.aliases):
            return existing

    best_match: Entity | None = None
    best_score = 0.0
    for existing in existing_entities:
        score = SequenceMatcher(
            None, target, existing.canonical_name.strip().casefold()
        ).ratio()
        if score >= similarity_threshold and score > best_score:
            best_match = existing
            best_score = score
    return best_match
