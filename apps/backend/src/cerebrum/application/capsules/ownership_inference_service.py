"""``OwnershipInferenceService``: CIS Phase 5 Prompt 3's Inference
Engine — Repository/Service/API/Database/Architectural Ownership.
Builds on the same entity-co-occurrence evidence
cerebrum.application.capsules.expertise_inference_service.ExpertiseInferenceService
uses (see that module's docstring for the honest limitation this
shares), but only treats co-occurrence as *ownership* signal once it
crosses :data:`_MIN_OWNERSHIP_SCORE` — and, unlike expertise, actually
writes the inference back into the knowledge graph as a real
``OWNERSHIP``
:class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
edge via
cerebrum.application.capsules.capsule_graph_service.CapsuleGraphService,
so "Knowledge Graph Integration: Extend the graph with... ownership
edges" is a genuine, persisted side effect of running inference, not
only a capsule-local computation.

``OwnershipInsight.share`` — this person's fraction of the total
ownership signal observed for the owned entity, across *every* person
with an ``OWNERSHIP`` edge to it — is computed here (not deferred to
:class:`~cerebrum.application.capsules.risk_analysis_service.RiskAnalysisService`)
because it only needs one entity's neighborhood, not a workspace-wide
scan; ``RiskAnalysisService`` reads the already-persisted edges this
service writes rather than recomputing shares itself.
"""

import uuid
from collections import defaultdict

from cerebrum.application.capsules.capsule_graph_service import CapsuleGraphService
from cerebrum.application.capsules.dataclasses_ import EvidenceRef, OwnershipInsight
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.entity import Entity, EntityType
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
_OWNERSHIP_ENTITY_TYPES = frozenset(
    {
        EntityType.TECHNOLOGY.value,
        EntityType.PRODUCT.value,
        EntityType.PROJECT.value,
        EntityType.CUSTOM.value,
    }
)
_OWNERSHIP_CATEGORIES = frozenset(
    {"repository", "service", "api", "database", "architecture"}
)
_FREQUENCY_SATURATION = 5
# The minimum evidence strength before co-occurrence is treated as
# ownership signal rather than a merely expertise-adjacent mention —
# ownership is a stronger, graph-persisted claim than expertise, so it
# earns a higher bar than any expertise score is held to.
_MIN_OWNERSHIP_SCORE = 0.3


class OwnershipInferenceService:
    def __init__(
        self,
        *,
        relationship_service: RelationshipService,
        entity_service: EntityService,
        capsule_graph_service: CapsuleGraphService,
    ) -> None:
        self._relationships = relationship_service
        self._entities = entity_service
        self._graph = capsule_graph_service

    async def infer(
        self,
        person_entity_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
        persist_edges: bool = True,
    ) -> list[OwnershipInsight]:
        relationships = await self._relationships.list_for_entity(
            person_entity_id, workspace_id=workspace_id
        )
        grouped = _group_by_other_entity(relationships, person_entity_id)

        insights: list[OwnershipInsight] = []
        for other_entity_id, edges in grouped.items():
            other = await self._entities.get(other_entity_id, workspace_id=workspace_id)
            if other.entity_type not in _OWNERSHIP_ENTITY_TYPES:
                continue

            average_confidence = sum(edge.confidence for edge in edges) / len(edges)
            frequency_weight = min(1.0, len(edges) / _FREQUENCY_SATURATION)
            score = round(average_confidence * frequency_weight, 4)
            if score < _MIN_OWNERSHIP_SCORE:
                continue

            if persist_edges:
                await self._graph.upsert_edge(
                    source_entity_id=person_entity_id,
                    target_entity_id=other.id,
                    relationship_type=RelationshipType.OWNERSHIP,
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                    confidence=score,
                    evidence_text=(
                        f"Co-occurred with '{other.canonical_name}' across "
                        f"{len(edges)} recorded relationship(s)."
                    ),
                    created_by=created_by,
                )

            share = await self._compute_share(
                other.id, person_entity_id, score, workspace_id=workspace_id
            )
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
                OwnershipInsight(
                    entity_id=other.id,
                    canonical_name=other.canonical_name,
                    entity_type=other.entity_type,
                    ownership_category=_categorize(other),
                    share=share,
                    score=score,
                    evidence=evidence,
                )
            )

        insights.sort(key=lambda insight: insight.score, reverse=True)
        return insights

    async def _compute_share(
        self,
        target_entity_id: uuid.UUID,
        this_person_entity_id: uuid.UUID,
        this_score: float,
        *,
        workspace_id: uuid.UUID,
    ) -> float:
        edges = await self._relationships.list_for_entity(
            target_entity_id, workspace_id=workspace_id
        )
        weights: dict[uuid.UUID, float] = {
            edge.source_entity_id: edge.confidence
            for edge in edges
            if edge.relationship_type == RelationshipType.OWNERSHIP.value
            and edge.target_entity_id == target_entity_id
        }
        # The edge for this refresh pass may not be persisted yet (or
        # this call may be a dry run with persist_edges=False) — the
        # person's own just-computed score always counts toward the
        # denominator regardless.
        weights[this_person_entity_id] = this_score
        total = sum(weights.values())
        if total <= 0:
            return 0.0
        return round(weights[this_person_entity_id] / total, 4)


def _categorize(entity: Entity) -> str:
    if entity.custom_type_name:
        normalized = entity.custom_type_name.strip().lower()
        if normalized in _OWNERSHIP_CATEGORIES:
            return normalized
    return "general"


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
