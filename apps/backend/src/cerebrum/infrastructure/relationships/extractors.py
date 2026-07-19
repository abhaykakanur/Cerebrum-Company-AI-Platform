"""Rule-based relationship extraction — CIS Phase 3 Prompt 1's
Relationship Extraction framework.
:class:`CueBasedRelationshipExtractor` looks for a configurable cue
phrase (e.g. "reports to", "owns", "depends on") in the text between
two entities that co-occur within a configurable proximity window; a
pair that co-occurs with no matching cue still yields a generic
``MENTIONS`` relationship at lower confidence (disable via
``emit_mentions_fallback=False``). Purely lexical — no ML/LLM, per this
milestone's explicit "DO NOT IMPLEMENT: LLM reasoning" boundary.
"""

from typing import Protocol

from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.infrastructure.entities.results import ExtractedEntity
from cerebrum.infrastructure.relationships.results import ExtractedRelationship

_DEFAULT_PROXIMITY_WINDOW = 200
_CUE_MATCH_CONFIDENCE = 0.7
_COOCCURRENCE_CONFIDENCE = 0.3

_DEFAULT_CUE_PHRASES: dict[RelationshipType, list[str]] = {
    RelationshipType.REPORTS_TO: ["reports to", "reporting to"],
    RelationshipType.OWNERSHIP: ["owns", "is owned by", "ownership of"],
    RelationshipType.MEMBERSHIP: ["member of", "is a member of", "belongs to"],
    RelationshipType.DEPENDENCY: ["depends on", "dependent on", "requires"],
    RelationshipType.PARENT_CHILD: ["parent of", "child of", "subsidiary of"],
    RelationshipType.COLLABORATION: [
        "collaborates with",
        "in collaboration with",
        "works with",
    ],
    RelationshipType.USES: ["uses", "utilizing", "built with"],
    RelationshipType.PRODUCED_BY: ["produced by", "created by", "developed by"],
    RelationshipType.REFERENCES: ["references", "refers to", "cites"],
}


class RelationshipExtractor(Protocol):
    def extract(
        self, text: str, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelationship]: ...


class CueBasedRelationshipExtractor:
    """``cue_phrases`` fully replaces the default phrase list for any
    :class:`~cerebrum.infrastructure.database.models.relationship.RelationshipType`
    key it supplies — same "replace, not merge" convention as
    cerebrum.infrastructure.entities.extractors.RegexEntityExtractor.
    """

    def __init__(
        self,
        cue_phrases: dict[RelationshipType, list[str]] | None = None,
        *,
        proximity_window: int = _DEFAULT_PROXIMITY_WINDOW,
        emit_mentions_fallback: bool = True,
    ) -> None:
        self._cue_phrases = {**_DEFAULT_CUE_PHRASES, **(cue_phrases or {})}
        self._proximity_window = proximity_window
        self._emit_mentions_fallback = emit_mentions_fallback

    def extract(
        self, text: str, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelationship]:
        results: list[ExtractedRelationship] = []
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                relationship = self._relate_pair(text, entities, i, j)
                if relationship is not None:
                    results.append(relationship)
        return results

    def _relate_pair(
        self, text: str, entities: list[ExtractedEntity], i: int, j: int
    ) -> ExtractedRelationship | None:
        a, b = entities[i], entities[j]
        if (
            a.entity_type == b.entity_type
            and a.canonical_name.casefold() == b.canonical_name.casefold()
        ):
            return None
        if abs(a.start_offset - b.start_offset) > self._proximity_window:
            return None

        if a.start_offset <= b.start_offset:
            first, second, source_index, target_index = a, b, i, j
        else:
            first, second, source_index, target_index = b, a, j, i

        between = text[first.end_offset : second.start_offset]
        cue_match = self._find_cue(between)
        evidence = text[first.start_offset : second.end_offset]

        if cue_match is not None:
            return ExtractedRelationship(
                source_index=source_index,
                target_index=target_index,
                relationship_type=cue_match,
                confidence=_CUE_MATCH_CONFIDENCE,
                evidence=evidence,
            )
        if self._emit_mentions_fallback:
            return ExtractedRelationship(
                source_index=source_index,
                target_index=target_index,
                relationship_type=RelationshipType.MENTIONS,
                confidence=_COOCCURRENCE_CONFIDENCE,
                evidence=evidence,
            )
        return None

    def _find_cue(self, between: str) -> RelationshipType | None:
        lowered = between.casefold()
        for relationship_type, phrases in self._cue_phrases.items():
            if any(phrase in lowered for phrase in phrases):
                return relationship_type
        return None
