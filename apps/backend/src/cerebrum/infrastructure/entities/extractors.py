"""Configurable, rule-based entity extractors — CIS Phase 3 Prompt 1's
Entity Extraction framework. Two complementary strategies, composed by
:class:`CompositeEntityExtractor`:

* :class:`RegexEntityExtractor` — for entity types with a reliable
  textual pattern (dates, organization-suffix names). Coarse by
  design: e.g. its default ``PERSON`` pattern (two consecutive
  capitalized words) will both miss real names and match false
  positives (a sentence-initial capitalized phrase) — a real NLU model
  would do better, but this milestone's Non-Objectives explicitly
  exclude one ("DO NOT IMPLEMENT: LLM reasoning"). Callers needing
  better precision configure their own patterns, or lean on the
  dictionary extractor instead.
* :class:`DictionaryEntityExtractor` — exact, case-insensitive
  vocabulary matching, for types no regex can reliably identify (team
  names, project names, product names, customer names, ...) — the
  caller supplies the known terms (e.g. seeded from an existing CRM/
  project list), and matching is exact by construction, not heuristic.
"""

import re
from dataclasses import dataclass
from typing import Protocol

from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.entities.results import ExtractedEntity

_CONTEXT_RADIUS = 80
"""Characters of surrounding text captured as ``ExtractedEntity.context``
on either side of a match — enough for
cerebrum.infrastructure.relationships.extractors to look for a cue
phrase nearby, without capturing the whole document.
"""


class EntityExtractor(Protocol):
    def extract(self, text: str) -> list[ExtractedEntity]: ...


def _context_window(text: str, start: int, end: int) -> str:
    return text[max(0, start - _CONTEXT_RADIUS) : min(len(text), end + _CONTEXT_RADIUS)]


@dataclass(frozen=True, slots=True)
class _PatternRule:
    pattern: re.Pattern[str]
    confidence: float


_DEFAULT_PATTERNS: dict[EntityType, list[_PatternRule]] = {
    EntityType.DATE: [
        _PatternRule(re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), 0.9),
        _PatternRule(
            re.compile(
                r"\b(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
            ),
            0.9,
        ),
    ],
    EntityType.ORGANIZATION: [
        _PatternRule(
            re.compile(
                r"\b[A-Z][\w&]*(?:\s+[A-Z][\w&]*)*\s+"
                r"(?:Inc|LLC|Corp|Corporation|Ltd|Company|Co|GmbH)\.?\b"
            ),
            0.75,
        ),
    ],
    EntityType.PERSON: [
        _PatternRule(re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"), 0.5),
    ],
}


class RegexEntityExtractor:
    """``patterns`` fully replaces the default rule set for any
    :class:`~cerebrum.infrastructure.database.models.entity.EntityType`
    key it supplies (not merged rule-by-rule) — a caller tuning
    ``PERSON`` detection provides its own complete pattern list for
    that type; every other type keeps this extractor's defaults.
    """

    def __init__(
        self, patterns: dict[EntityType, list[_PatternRule]] | None = None
    ) -> None:
        self._patterns = {**_DEFAULT_PATTERNS, **(patterns or {})}

    def extract(self, text: str) -> list[ExtractedEntity]:
        results: list[ExtractedEntity] = []
        seen: set[tuple[EntityType, str]] = set()
        for entity_type, rules in self._patterns.items():
            for rule in rules:
                for match in rule.pattern.finditer(text):
                    canonical_name = match.group(0).strip().rstrip(".")
                    key = (entity_type, canonical_name.casefold())
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(
                        ExtractedEntity(
                            entity_type=entity_type,
                            canonical_name=canonical_name,
                            confidence=rule.confidence,
                            context=_context_window(text, match.start(), match.end()),
                            start_offset=match.start(),
                            end_offset=match.end(),
                        )
                    )
        return results


_DICTIONARY_MATCH_CONFIDENCE = 0.85


class DictionaryEntityExtractor:
    """Exact, case-insensitive, whole-word vocabulary matching —
    ``vocabulary`` covers the fourteen named
    :class:`~cerebrum.infrastructure.database.models.entity.EntityType`
    values; ``custom_vocabulary`` (keyed by the caller's own type name)
    covers :data:`~cerebrum.infrastructure.database.models.entity.EntityType.CUSTOM`.
    """

    def __init__(
        self,
        vocabulary: dict[EntityType, set[str]] | None = None,
        custom_vocabulary: dict[str, set[str]] | None = None,
    ) -> None:
        self._vocabulary = vocabulary or {}
        self._custom_vocabulary = custom_vocabulary or {}

    def extract(self, text: str) -> list[ExtractedEntity]:
        results: list[ExtractedEntity] = []
        for entity_type, terms in self._vocabulary.items():
            results.extend(self._match_terms(text, terms, entity_type, None))
        for custom_type_name, terms in self._custom_vocabulary.items():
            results.extend(
                self._match_terms(text, terms, EntityType.CUSTOM, custom_type_name)
            )
        return results

    @staticmethod
    def _match_terms(
        text: str,
        terms: set[str],
        entity_type: EntityType,
        custom_type_name: str | None,
    ) -> list[ExtractedEntity]:
        matches = []
        for term in terms:
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                matches.append(
                    ExtractedEntity(
                        entity_type=entity_type,
                        custom_type_name=custom_type_name,
                        canonical_name=term,
                        confidence=_DICTIONARY_MATCH_CONFIDENCE,
                        context=_context_window(text, match.start(), match.end()),
                        start_offset=match.start(),
                        end_offset=match.end(),
                    )
                )
        return matches


class CompositeEntityExtractor:
    """Runs every configured extractor and merges their results,
    collapsing duplicate ``(entity_type, custom_type_name,
    canonical_name)`` mentions down to the single highest-confidence
    occurrence — the "Support configurable extractors" requirement:
    a caller composes whichever extractors it needs (typically one
    :class:`RegexEntityExtractor` plus one :class:`DictionaryEntityExtractor`,
    but any :class:`EntityExtractor` implementation works).
    """

    def __init__(self, extractors: list[EntityExtractor]) -> None:
        self._extractors = extractors

    def extract(self, text: str) -> list[ExtractedEntity]:
        best: dict[tuple[EntityType, str | None, str], ExtractedEntity] = {}
        for extractor in self._extractors:
            for candidate in extractor.extract(text):
                key = (
                    candidate.entity_type,
                    candidate.custom_type_name,
                    candidate.canonical_name.casefold(),
                )
                existing = best.get(key)
                if existing is None or candidate.confidence > existing.confidence:
                    best[key] = candidate
        return list(best.values())
