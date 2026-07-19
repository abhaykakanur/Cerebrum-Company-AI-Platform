"""``ExpertiseInferenceService``: CIS Phase 5 Prompt 3's Inference
Engine — Subject Matter Expertise. Infers expertise areas from real
:class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
edges already touching the employee's linked PERSON entity —
``MENTIONS``/``REFERENCES``/``COLLABORATION``/``USES`` edges to
``TECHNOLOGY``/``PRODUCT``/``PROJECT`` entities, produced by CIS Phase
3's extraction pipeline from every document this workspace has
ingested (including connector-synced ones — CIS Phase 5 Prompt 1).

**Honest limitation**: this is entity co-occurrence evidence, not
commit-level attribution — Phase 5 Prompt 1's connectors do not
preserve structured per-item author identity when normalizing external
content into documents (only body/title survive), so "this person
authored N commits in this repo" is not a claim this engine can make.
What it *can* and does claim, with real evidence behind every score: a
document this workspace ingested mentions/references both this person
and this technology/product/project closely enough for CIS Phase 3's
extractor to have recorded a relationship between them. Every insight
cites the exact relationship rows behind its score.
"""

import uuid
from collections import defaultdict

from cerebrum.application.capsules.dataclasses_ import EvidenceRef, ExpertiseInsight
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import (
    Relationship,
    RelationshipType,
)

_RELEVANT_TYPES = frozenset(
    {
        RelationshipType.MENTIONS.value,
        RelationshipType.REFERENCES.value,
        RelationshipType.COLLABORATION.value,
        RelationshipType.USES.value,
    }
)
_EXPERTISE_ENTITY_TYPES = frozenset(
    {EntityType.TECHNOLOGY.value, EntityType.PRODUCT.value, EntityType.PROJECT.value}
)
# A person needs this many distinct supporting relationships before an
# expertise score reaches its full frequency weight — chosen so a
# single incidental mention does not read as "expert," while genuine,
# repeated co-occurrence saturates quickly rather than requiring an
# unrealistically large evidence trail.
_FREQUENCY_SATURATION = 5


class ExpertiseInferenceService:
    def __init__(
        self,
        *,
        relationship_service: RelationshipService,
        entity_service: EntityService,
    ) -> None:
        self._relationships = relationship_service
        self._entities = entity_service

    async def infer(
        self, person_entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[ExpertiseInsight]:
        relationships = await self._relationships.list_for_entity(
            person_entity_id, workspace_id=workspace_id
        )
        grouped = _group_by_other_entity(relationships, person_entity_id)

        insights: list[ExpertiseInsight] = []
        for other_entity_id, edges in grouped.items():
            other = await self._entities.get(other_entity_id, workspace_id=workspace_id)
            if other.entity_type not in _EXPERTISE_ENTITY_TYPES:
                continue

            average_confidence = sum(edge.confidence for edge in edges) / len(edges)
            frequency_weight = min(1.0, len(edges) / _FREQUENCY_SATURATION)
            score = round(average_confidence * frequency_weight, 4)

            evidence = [
                EvidenceRef(
                    description=(
                        f"{edge.relationship_type} relationship with "
                        f"'{other.canonical_name}'"
                        + (f": {edge.evidence}" if edge.evidence else "")
                    ),
                    confidence=edge.confidence,
                    relationship_id=edge.id,
                    entity_id=other.id,
                    document_id=edge.source_document_id,
                    occurred_at=edge.valid_from or edge.created_at,
                )
                for edge in edges
            ]
            insights.append(
                ExpertiseInsight(
                    entity_id=other.id,
                    canonical_name=other.canonical_name,
                    entity_type=other.entity_type,
                    score=score,
                    evidence=evidence,
                )
            )

        insights.sort(key=lambda insight: insight.score, reverse=True)
        return insights


def _group_by_other_entity(
    relationships: list[Relationship], person_entity_id: uuid.UUID
) -> dict[uuid.UUID, list[Relationship]]:
    grouped: dict[uuid.UUID, list[Relationship]] = defaultdict(list)
    for relationship in relationships:
        if relationship.relationship_type not in _RELEVANT_TYPES:
            continue
        other_entity_id = (
            relationship.target_entity_id
            if relationship.source_entity_id == person_entity_id
            else relationship.source_entity_id
        )
        grouped[other_entity_id].append(relationship)
    return grouped
