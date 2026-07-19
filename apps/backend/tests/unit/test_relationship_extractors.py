"""Proves CIS Phase 3 Prompt 1's Relationship Extraction framework:
cue-phrase matching with correct directionality, proximity windowing,
the generic ``MENTIONS`` fallback, and disabling that fallback.
"""

import pytest

from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.infrastructure.entities.results import ExtractedEntity
from cerebrum.infrastructure.relationships.extractors import (
    CueBasedRelationshipExtractor,
)

pytestmark = pytest.mark.unit


def _entity(name: str, start: int, end: int) -> ExtractedEntity:
    from cerebrum.infrastructure.database.models.entity import EntityType

    return ExtractedEntity(
        entity_type=EntityType.PERSON,
        canonical_name=name,
        confidence=0.6,
        context=name,
        start_offset=start,
        end_offset=end,
    )


def test_finds_a_cue_phrase_and_orients_source_before_target() -> None:
    text = "Alice Johnson reports to Bob Williams."
    alice = _entity("Alice Johnson", 0, 13)
    bob = _entity("Bob Williams", 25, 37)

    results = CueBasedRelationshipExtractor().extract(text, [alice, bob])

    assert len(results) == 1
    assert results[0].relationship_type == RelationshipType.REPORTS_TO
    assert results[0].source_index == 0
    assert results[0].target_index == 1
    assert results[0].confidence == 0.7


def test_orients_correctly_regardless_of_entity_list_order() -> None:
    text = "Alice Johnson reports to Bob Williams."
    bob = _entity("Bob Williams", 25, 37)
    alice = _entity("Alice Johnson", 0, 13)

    results = CueBasedRelationshipExtractor().extract(text, [bob, alice])

    assert len(results) == 1
    assert results[0].source_index == 1  # alice, at index 1 in this ordering
    assert results[0].target_index == 0  # bob


def test_falls_back_to_mentions_when_no_cue_phrase_is_found() -> None:
    text = "Alice Johnson and Bob Williams attended the meeting."
    alice = _entity("Alice Johnson", 0, 13)
    bob = _entity("Bob Williams", 19, 31)

    results = CueBasedRelationshipExtractor().extract(text, [alice, bob])

    assert len(results) == 1
    assert results[0].relationship_type == RelationshipType.MENTIONS
    assert results[0].confidence == 0.3


def test_mentions_fallback_can_be_disabled() -> None:
    text = "Alice Johnson and Bob Williams attended the meeting."
    alice = _entity("Alice Johnson", 0, 13)
    bob = _entity("Bob Williams", 19, 31)

    results = CueBasedRelationshipExtractor(emit_mentions_fallback=False).extract(
        text, [alice, bob]
    )

    assert results == []


def test_entities_outside_the_proximity_window_are_not_related() -> None:
    text = "Alice Johnson works here." + (" " * 300) + "Bob Williams works elsewhere."
    alice = _entity("Alice Johnson", 0, 13)
    bob_start = text.index("Bob Williams")
    bob = _entity("Bob Williams", bob_start, bob_start + 12)

    results = CueBasedRelationshipExtractor(proximity_window=200).extract(
        text, [alice, bob]
    )

    assert results == []


def test_custom_cue_phrases_fully_replace_the_default_for_that_type() -> None:
    text = "Alice Johnson champions Bob Williams."
    alice = _entity("Alice Johnson", 0, 13)
    bob = _entity("Bob Williams", 24, 36)

    extractor = CueBasedRelationshipExtractor(
        cue_phrases={RelationshipType.COLLABORATION: ["champions"]}
    )
    results = extractor.extract(text, [alice, bob])

    assert len(results) == 1
    assert results[0].relationship_type == RelationshipType.COLLABORATION


def test_does_not_relate_the_same_entity_to_itself() -> None:
    text = "Alice Johnson and Alice Johnson."
    first = _entity("Alice Johnson", 0, 13)
    second = _entity("Alice Johnson", 19, 32)

    results = CueBasedRelationshipExtractor().extract(text, [first, second])

    assert results == []
