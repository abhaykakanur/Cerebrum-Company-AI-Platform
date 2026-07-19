"""``RiskAnalysisService``: CIS Phase 5 Prompt 3's Risk Analysis — Bus
Factor, Knowledge Concentration, Single-Owner Detection, Critical
Dependency Detection, Coverage Scoring, and Successor Readiness. Reads
only the ``OWNERSHIP``/``DEPENDENCY``
:class:`~cerebrum.infrastructure.database.models.relationship.Relationship`
edges
cerebrum.application.capsules.ownership_inference_service.OwnershipInferenceService
(and CIS Phase 3's own extraction pipeline, for ``DEPENDENCY``) already
persisted — computes nothing new about entities, only aggregates
already-evidenced ownership signal workspace-wide.

**Bus factor** here is the standard heuristic: the fewest people whose
combined ownership share covers at least half of an entity's total
observed ownership signal — one dominant owner (share > 0.5) gives a
bus factor of 1; two closely-split owners give 2; and so on.
"""

import uuid

from cerebrum.application.capsules.dataclasses_ import (
    BusFactorResult,
    CoverageReport,
    OwnerShare,
)
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import RelationshipType
from cerebrum.repositories.contracts import FilterOperator, FilterSpec, Pagination

_OWNABLE_ENTITY_TYPES = (
    EntityType.TECHNOLOGY.value,
    EntityType.PRODUCT.value,
    EntityType.PROJECT.value,
    EntityType.CUSTOM.value,
)
# An entity needs at least this many other entities depending on it
# before a low bus factor is worth flagging as a *critical* dependency
# risk rather than merely a single-owner one — a low-bus-factor entity
# nothing else depends on is a succession risk, not a blast-radius risk.
_MIN_DEPENDENTS_FOR_CRITICALITY = 2
_SCAN_PAGE_SIZE = 200


class RiskAnalysisService:
    def __init__(
        self,
        *,
        relationship_service: RelationshipService,
        entity_service: EntityService,
    ) -> None:
        self._relationships = relationship_service
        self._entities = entity_service

    async def bus_factor(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> BusFactorResult:
        entity = await self._entities.get(entity_id, workspace_id=workspace_id)
        edges = await self._relationships.list_for_entity(
            entity_id, workspace_id=workspace_id
        )
        weights: dict[uuid.UUID, float] = {}
        for edge in edges:
            if (
                edge.relationship_type != RelationshipType.OWNERSHIP.value
                or edge.target_entity_id != entity_id
            ):
                continue
            weights[edge.source_entity_id] = max(
                weights.get(edge.source_entity_id, 0.0), edge.confidence
            )

        total = sum(weights.values())
        owners: list[OwnerShare] = []
        if total > 0:
            for person_entity_id, weight in sorted(
                weights.items(), key=lambda item: item[1], reverse=True
            ):
                person = await self._entities.get(
                    person_entity_id, workspace_id=workspace_id
                )
                owners.append(
                    OwnerShare(
                        person_entity_id=person_entity_id,
                        canonical_name=person.canonical_name,
                        share=round(weight / total, 4),
                    )
                )

        bus_factor_count = _bus_factor_from_shares([owner.share for owner in owners])
        return BusFactorResult(
            entity_id=entity.id,
            canonical_name=entity.canonical_name,
            bus_factor=bus_factor_count,
            owners=owners,
            risk_level=_risk_level(bus_factor_count),
        )

    async def _list_ownable_entity_ids(
        self, *, workspace_id: uuid.UUID
    ) -> list[uuid.UUID]:
        page = await self._entities.list_in_workspace(
            workspace_id=workspace_id,
            pagination=Pagination(page=1, page_size=_SCAN_PAGE_SIZE),
            filters=[
                FilterSpec(
                    field="entity_type",
                    operator=FilterOperator.IN,
                    value=list(_OWNABLE_ENTITY_TYPES),
                )
            ],
        )
        return [entity.id for entity in page.items]

    async def coverage_report(self, *, workspace_id: uuid.UUID) -> CoverageReport:
        """Knowledge Concentration / Coverage Scoring / Single-Owner
        Detection, together: every ownable entity in the workspace
        (scanning up to :data:`_SCAN_PAGE_SIZE` of them — a workspace
        with more would need a dedicated aggregate query, not
        implemented at this milestone) gets a
        :meth:`bus_factor` computed; ``coverage_score`` is the fraction
        that have *any* recorded owner at all.
        """
        entity_ids = await self._list_ownable_entity_ids(workspace_id=workspace_id)
        results = [
            await self.bus_factor(entity_id, workspace_id=workspace_id)
            for entity_id in entity_ids
        ]
        covered = [result for result in results if result.bus_factor >= 1]
        single_owner = [result for result in results if result.bus_factor == 1]
        coverage_score = round(len(covered) / len(results), 4) if results else 0.0
        return CoverageReport(
            workspace_id=workspace_id,
            total_owned_entities=len(results),
            covered_entities=len(covered),
            coverage_score=coverage_score,
            single_owner_entities=single_owner,
        )

    async def critical_dependencies(
        self, *, workspace_id: uuid.UUID
    ) -> list[BusFactorResult]:
        """Critical Dependency Detection: an ownable entity that at
        least :data:`_MIN_DEPENDENTS_FOR_CRITICALITY` other entities
        depend on (``DEPENDENCY`` edges targeting it — CIS Phase 3's
        extraction pipeline, not this service, produces those), whose
        bus factor is ``critical`` or ``high`` — high blast radius
        combined with low ownership resilience.
        """
        entity_ids = await self._list_ownable_entity_ids(workspace_id=workspace_id)
        critical: list[BusFactorResult] = []
        for entity_id in entity_ids:
            edges = await self._relationships.list_for_entity(
                entity_id, workspace_id=workspace_id
            )
            dependents = [
                edge
                for edge in edges
                if edge.relationship_type == RelationshipType.DEPENDENCY.value
                and edge.target_entity_id == entity_id
            ]
            if len(dependents) < _MIN_DEPENDENTS_FOR_CRITICALITY:
                continue
            result = await self.bus_factor(entity_id, workspace_id=workspace_id)
            if result.risk_level in {"critical", "high"}:
                critical.append(result)
        return critical

    async def successor_readiness(
        self, entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> bool:
        result = await self.bus_factor(entity_id, workspace_id=workspace_id)
        return result.bus_factor >= 2


def _bus_factor_from_shares(shares: list[float]) -> int:
    if not shares:
        return 0
    cumulative = 0.0
    count = 0
    for share in sorted(shares, reverse=True):
        cumulative += share
        count += 1
        if cumulative >= 0.5:
            break
    return count


def _risk_level(bus_factor: int) -> str:
    if bus_factor <= 0:
        return "critical"
    if bus_factor == 1:
        return "high"
    if bus_factor == 2:
        return "medium"
    return "low"
