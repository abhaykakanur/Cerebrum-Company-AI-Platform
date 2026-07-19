"""Proves CIS Phase 3 Prompt 1's Entity Extraction framework: the
default regex heuristics (dates, organization suffixes, person-name
pairs), exact vocabulary matching, and composite merge/dedup-by-
confidence across extractors.
"""

import pytest

from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.entities.extractors import (
    CompositeEntityExtractor,
    DictionaryEntityExtractor,
    RegexEntityExtractor,
)

pytestmark = pytest.mark.unit


def test_regex_extractor_finds_iso_dates() -> None:
    result = RegexEntityExtractor().extract("The meeting was held on 2026-03-05.")
    dates = [e for e in result if e.entity_type == EntityType.DATE]
    assert dates
    assert dates[0].canonical_name == "2026-03-05"
    assert dates[0].confidence == 0.9


def test_regex_extractor_finds_organization_suffixes() -> None:
    result = RegexEntityExtractor().extract("We partnered with Acme Corp on this.")
    orgs = [e for e in result if e.entity_type == EntityType.ORGANIZATION]
    assert any(e.canonical_name == "Acme Corp" for e in orgs)


def test_regex_extractor_offsets_round_trip() -> None:
    text = "Alice Johnson met with Bob Smith on 2026-01-01."
    result = RegexEntityExtractor().extract(text)
    for entity in result:
        assert text[entity.start_offset : entity.end_offset] == entity.canonical_name


def test_regex_extractor_deduplicates_repeated_mentions_within_one_call() -> None:
    text = "Acme Corp signed the deal. Acme Corp will start next month."
    result = RegexEntityExtractor().extract(text)
    org_mentions = [
        e
        for e in result
        if e.canonical_name == "Acme Corp" and e.entity_type == EntityType.ORGANIZATION
    ]
    assert len(org_mentions) == 1


def test_custom_patterns_fully_replace_the_default_for_that_type() -> None:
    import re

    from cerebrum.infrastructure.entities.extractors import _PatternRule

    custom = RegexEntityExtractor(
        patterns={
            EntityType.DATE: [_PatternRule(re.compile(r"\bQ[1-4] \d{4}\b"), 0.95)]
        }
    )
    result = custom.extract("Targeting Q3 2026 for launch, not 2026-03-05.")
    dates = [e for e in result if e.entity_type == EntityType.DATE]
    assert [d.canonical_name for d in dates] == ["Q3 2026"]


def test_dictionary_extractor_matches_exact_vocabulary_case_insensitively() -> None:
    extractor = DictionaryEntityExtractor(
        vocabulary={EntityType.TECHNOLOGY: {"Python", "Kubernetes"}}
    )
    result = extractor.extract("We deploy python workloads on Kubernetes.")
    # canonical_name is the vocabulary's own term, not whatever case
    # variant matched in the text — case-insensitive matching, canonical
    # (not literal) naming.
    names = {e.canonical_name for e in result}
    assert names == {"Python", "Kubernetes"}
    assert all(e.confidence == 0.85 for e in result)


def test_dictionary_extractor_supports_custom_type_vocabulary() -> None:
    extractor = DictionaryEntityExtractor(
        custom_vocabulary={"Initiative": {"Project Falcon"}}
    )
    result = extractor.extract("Project Falcon kicks off next sprint.")
    assert len(result) == 1
    assert result[0].entity_type == EntityType.CUSTOM
    assert result[0].custom_type_name == "Initiative"


def test_dictionary_extractor_does_not_match_partial_words() -> None:
    extractor = DictionaryEntityExtractor(vocabulary={EntityType.TECHNOLOGY: {"Go"}})
    result = extractor.extract("We are going forward with Golang, not Go.")
    assert len(result) == 1
    assert result[0].start_offset == result[0].end_offset - 2


def test_composite_extractor_merges_and_keeps_highest_confidence() -> None:
    weak = DictionaryEntityExtractor(
        vocabulary={EntityType.ORGANIZATION: {"Acme Corp"}}
    )

    class _StrongerExtractor:
        def extract(self, text: str):
            from cerebrum.infrastructure.entities.results import ExtractedEntity

            return [
                ExtractedEntity(
                    entity_type=EntityType.ORGANIZATION,
                    canonical_name="Acme Corp",
                    confidence=0.99,
                    context="Acme Corp",
                    start_offset=0,
                    end_offset=9,
                )
            ]

    composite = CompositeEntityExtractor([weak, _StrongerExtractor()])
    result = composite.extract("Acme Corp is here.")
    assert len(result) == 1
    assert result[0].confidence == 0.99
