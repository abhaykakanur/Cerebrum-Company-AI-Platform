"""Proves CIS Phase 3 Prompt 1's Deduplication: exact match, alias
match, configurable similarity threshold, and "no match" when nothing
is close enough.
"""

import uuid

import pytest

from cerebrum.application.knowledge_graph.deduplication import find_duplicate
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
from cerebrum.infrastructure.entities.results import ExtractedEntity

pytestmark = pytest.mark.unit


def _entity(canonical_name: str, aliases: list[str] | None = None) -> Entity:
    return Entity(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        entity_type=EntityType.ORGANIZATION.value,
        canonical_name=canonical_name,
        aliases=aliases or [],
        confidence=0.8,
        provenance=[],
    )


def _candidate(canonical_name: str) -> ExtractedEntity:
    return ExtractedEntity(
        entity_type=EntityType.ORGANIZATION,
        canonical_name=canonical_name,
        confidence=0.7,
        context=canonical_name,
        start_offset=0,
        end_offset=len(canonical_name),
    )


def test_exact_match_is_case_insensitive() -> None:
    existing = _entity("Acme Corp")
    match = find_duplicate(_candidate("acme corp"), [existing])
    assert match is existing


def test_alias_match() -> None:
    existing = _entity("Acme Corporation", aliases=["Acme Corp", "Acme"])
    match = find_duplicate(_candidate("Acme Corp"), [existing])
    assert match is existing


def test_similarity_match_above_threshold() -> None:
    existing = _entity("Acme Corporation")
    match = find_duplicate(
        _candidate("Acme Corporatoin"),  # typo
        [existing],
        similarity_threshold=0.85,
    )
    assert match is existing


def test_no_match_below_similarity_threshold() -> None:
    existing = _entity("Acme Corporation")
    match = find_duplicate(
        _candidate("Totally Different Company"),
        [existing],
        similarity_threshold=0.85,
    )
    assert match is None


def test_picks_the_best_similarity_match_among_several_candidates() -> None:
    close = _entity("Acme Corporation")
    closer = _entity("Acme Corp")
    match = find_duplicate(
        _candidate("Acme Corp"), [close, closer], similarity_threshold=0.5
    )
    assert match is closer  # exact match wins over fuzzy


def test_empty_candidate_list_never_matches() -> None:
    assert find_duplicate(_candidate("Anything"), []) is None
