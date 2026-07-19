"""``EmployeeKnowledgeCapsuleService``: CIS Phase 5 Prompt 3's
orchestrator. Composes
:class:`~cerebrum.application.capsules.expertise_inference_service.ExpertiseInferenceService`,
:class:`~cerebrum.application.capsules.ownership_inference_service.OwnershipInferenceService`,
:class:`~cerebrum.application.capsules.organizational_memory_service.OrganizationalMemoryService`,
and
:class:`~cerebrum.application.capsules.capsule_graph_service.CapsuleGraphService`
— reuses CIS Phase 3's knowledge graph and CIS Phase 5 Prompt 1's
connector-synced documents entirely through those services; this class
contains no extraction, retrieval, or graph-write logic of its own.

**Identity linkage** is explicit and human-confirmed (see
:meth:`link_person_entity`), never automatic name-matching — see
cerebrum.infrastructure.database.models.capsule's docstring for why.
**Organizational role/responsibilities** are likewise operator-set
facts (see :meth:`update_profile`), not inferred — no evidence source
this milestone has access to can safely assert "this person's role is
X" without risking exactly the unsupported inference CIS Phase 5 Prompt
3 forbids. **Active projects**/**technical leadership**, by contrast,
*are* derived automatically during :meth:`refresh`, because they are
directly computable, evidence-backed subsets of the ownership map
(entities of type ``PROJECT``; entities this person holds a majority
ownership share of) rather than new claims.
"""

import uuid
from datetime import datetime
from typing import Any

from cerebrum.application.auth.audit_service import AuditService
from cerebrum.application.capsules.capsule_graph_service import CapsuleGraphService
from cerebrum.application.capsules.dataclasses_ import (
    CollaborationInsight,
    EvidenceRef,
)
from cerebrum.application.capsules.events import (
    CapsuleCreatedEvent,
    CapsuleLinkedEvent,
    CapsuleMarkedStaleEvent,
    CapsuleRefreshedEvent,
)
from cerebrum.application.capsules.expertise_inference_service import (
    ExpertiseInferenceService,
)
from cerebrum.application.capsules.organizational_memory_service import (
    OrganizationalMemoryService,
)
from cerebrum.application.capsules.ownership_inference_service import (
    OwnershipInferenceService,
)
from cerebrum.application.knowledge_graph.entity_service import EntityService
from cerebrum.application.knowledge_graph.relationship_service import (
    RelationshipService,
)
from cerebrum.events.dispatcher import EventDispatcher
from cerebrum.infrastructure.database.models.audit import AuditEventType
from cerebrum.infrastructure.database.models.capsule import EmployeeKnowledgeCapsule
from cerebrum.infrastructure.database.models.capsule_evidence import (
    CapsuleEvidenceRecord,
)
from cerebrum.infrastructure.database.models.capsule_timeline_event import (
    CapsuleTimelineEvent,
)
from cerebrum.infrastructure.database.models.entity import EntityType
from cerebrum.infrastructure.database.models.relationship import (
    Relationship,
    RelationshipType,
)
from cerebrum.repositories.contracts import FilterOperator, FilterSpec, Page, Pagination
from cerebrum.repositories.postgres.capsule_evidence_repository import (
    CapsuleEvidenceRepository,
)
from cerebrum.repositories.postgres.capsule_repository import CapsuleRepository
from cerebrum.repositories.postgres.capsule_timeline_repository import (
    CapsuleTimelineRepository,
)
from cerebrum.shared.errors.exceptions import NotFoundException, ValidationException
from cerebrum.utils.clock import utcnow

_MAJORITY_OWNERSHIP_SHARE = 0.5
_SEARCH_PAGE_SIZE = 200


class EmployeeKnowledgeCapsuleService:
    def __init__(
        self,
        *,
        capsule_repository: CapsuleRepository,
        evidence_repository: CapsuleEvidenceRepository,
        timeline_repository: CapsuleTimelineRepository,
        capsule_graph_service: CapsuleGraphService,
        expertise_service: ExpertiseInferenceService,
        ownership_service: OwnershipInferenceService,
        memory_service: OrganizationalMemoryService,
        relationship_service: RelationshipService,
        entity_service: EntityService,
        event_dispatcher: EventDispatcher,
        audit_service: AuditService,
    ) -> None:
        self._capsules = capsule_repository
        self._evidence = evidence_repository
        self._timeline = timeline_repository
        self._graph = capsule_graph_service
        self._expertise = expertise_service
        self._ownership = ownership_service
        self._memory = memory_service
        self._relationships = relationship_service
        self._entities = entity_service
        self._events = event_dispatcher
        self._audit = audit_service

    async def get_or_create_for_user(
        self,
        user_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID | None,
    ) -> EmployeeKnowledgeCapsule:
        existing = await self._capsules.get_by_user(user_id, workspace_id=workspace_id)
        if existing is not None:
            return existing

        capsule = await self._capsules.add(
            EmployeeKnowledgeCapsule(
                workspace_id=workspace_id,
                organization_id=organization_id,
                user_id=user_id,
                created_by=created_by,
                updated_by=created_by,
            )
        )
        self._events.publish(
            CapsuleCreatedEvent(
                capsule_id=capsule.id, workspace_id=workspace_id, user_id=user_id
            )
        )
        await self._audit.record(
            AuditEventType.CAPSULE_CREATED,
            user_id=created_by,
            workspace_id=workspace_id,
            metadata={"capsule_id": str(capsule.id), "subject_user_id": str(user_id)},
        )
        return capsule

    async def get(
        self,
        capsule_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        accessed_by: uuid.UUID | None = None,
    ) -> EmployeeKnowledgeCapsule:
        capsule = await self._capsules.get_by_id(capsule_id)
        if capsule is None or capsule.workspace_id != workspace_id:
            raise NotFoundException(f"No capsule with id {capsule_id}.")
        await self._audit.record(
            AuditEventType.CAPSULE_ACCESSED,
            user_id=accessed_by,
            workspace_id=workspace_id,
            metadata={"capsule_id": str(capsule.id)},
        )
        return capsule

    async def get_for_user(
        self,
        user_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        accessed_by: uuid.UUID | None = None,
    ) -> EmployeeKnowledgeCapsule:
        capsule = await self._capsules.get_by_user(user_id, workspace_id=workspace_id)
        if capsule is None:
            raise NotFoundException(f"No capsule for user {user_id}.")
        await self._audit.record(
            AuditEventType.CAPSULE_ACCESSED,
            user_id=accessed_by,
            workspace_id=workspace_id,
            metadata={"capsule_id": str(capsule.id)},
        )
        return capsule

    async def link_person_entity(
        self,
        capsule_id: uuid.UUID,
        entity_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        linked_by: uuid.UUID | None,
    ) -> EmployeeKnowledgeCapsule:
        capsule = await self._capsules.get_by_id(capsule_id)
        if capsule is None or capsule.workspace_id != workspace_id:
            raise NotFoundException(f"No capsule with id {capsule_id}.")
        entity = await self._graph.get_person_entity(
            entity_id, workspace_id=workspace_id
        )

        capsule.person_entity_id = entity.id
        capsule.is_stale = True
        capsule.stale_reason = "identity linked"
        capsule.updated_by = linked_by
        await self._capsules.update(capsule)

        await self._evidence.add(
            CapsuleEvidenceRecord(
                capsule_id=capsule.id,
                insight_type="identity_link",
                insight_key=entity.canonical_name,
                confidence=1.0,
                description=(
                    f"Linked to knowledge-graph identity '{entity.canonical_name}' "
                    "by an operator."
                ),
                entity_id=entity.id,
            )
        )

        self._events.publish(
            CapsuleLinkedEvent(
                capsule_id=capsule.id,
                workspace_id=workspace_id,
                person_entity_id=entity.id,
            )
        )
        await self._audit.record(
            AuditEventType.CAPSULE_LINKED,
            user_id=linked_by,
            workspace_id=workspace_id,
            metadata={
                "capsule_id": str(capsule.id),
                "person_entity_id": str(entity.id),
            },
        )
        return capsule

    async def update_profile(
        self,
        capsule_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        organizational_role: str | None = None,
        responsibilities: list[str] | None = None,
        updated_by: uuid.UUID | None,
    ) -> EmployeeKnowledgeCapsule:
        capsule = await self.get(capsule_id, workspace_id=workspace_id)
        if organizational_role is not None:
            capsule.organizational_role = organizational_role
        if responsibilities is not None:
            capsule.responsibilities = responsibilities
        capsule.updated_by = updated_by
        return await self._capsules.update(capsule)

    async def refresh(
        self,
        capsule_id: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
        organization_id: uuid.UUID,
        triggered_by: uuid.UUID | None,
    ) -> EmployeeKnowledgeCapsule:
        capsule = await self._capsules.get_by_id(capsule_id)
        if capsule is None or capsule.workspace_id != workspace_id:
            raise NotFoundException(f"No capsule with id {capsule_id}.")
        if capsule.person_entity_id is None:
            raise ValidationException(
                "Link a person entity before refreshing this capsule "
                "(see link_person_entity)."
            )

        expertise_insights = await self._expertise.infer(
            capsule.person_entity_id, workspace_id=workspace_id
        )
        ownership_insights = await self._ownership.infer(
            capsule.person_entity_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            created_by=triggered_by,
        )
        collaboration_insights = await self._infer_collaboration(
            capsule.person_entity_id, workspace_id=workspace_id
        )

        await self._evidence.delete_by_capsule_and_types(
            capsule.id, insight_types=["expertise", "ownership", "collaboration"]
        )
        for expertise_insight in expertise_insights:
            for reference in expertise_insight.evidence:
                await self._persist_evidence(
                    capsule.id, "expertise", expertise_insight.canonical_name, reference
                )
        for ownership_insight in ownership_insights:
            for reference in ownership_insight.evidence:
                await self._persist_evidence(
                    capsule.id, "ownership", ownership_insight.canonical_name, reference
                )
        for collaboration_insight in collaboration_insights:
            for reference in collaboration_insight.evidence:
                await self._persist_evidence(
                    capsule.id,
                    "collaboration",
                    collaboration_insight.canonical_name,
                    reference,
                )

        capsule.expertise_map = [
            {
                "entity_id": str(insight.entity_id),
                "canonical_name": insight.canonical_name,
                "entity_type": insight.entity_type,
                "score": insight.score,
                "evidence_count": len(insight.evidence),
            }
            for insight in expertise_insights
        ]
        capsule.ownership_map = [
            {
                "entity_id": str(insight.entity_id),
                "canonical_name": insight.canonical_name,
                "entity_type": insight.entity_type,
                "ownership_category": insight.ownership_category,
                "share": insight.share,
                "score": insight.score,
                "evidence_count": len(insight.evidence),
            }
            for insight in ownership_insights
        ]
        capsule.collaboration_network = [
            {
                "entity_id": str(insight.entity_id),
                "canonical_name": insight.canonical_name,
                "strength": insight.strength,
                "evidence_count": len(insight.evidence),
            }
            for insight in collaboration_insights
        ]
        capsule.active_projects = [
            item
            for item in capsule.ownership_map
            if item["entity_type"] == EntityType.PROJECT.value
        ]
        capsule.technical_leadership = [
            item
            for item in capsule.ownership_map
            if item["share"] >= _MAJORITY_OWNERSHIP_SHARE
        ]

        linked_at = await self._identity_link_timestamp(capsule.id)
        timeline_entries = self._memory.build_timeline(
            expertise_insights=expertise_insights,
            ownership_insights=ownership_insights,
            linked_at=linked_at,
        )
        await self._timeline.replace_for_capsule(
            capsule.id,
            [
                CapsuleTimelineEvent(
                    capsule_id=capsule.id,
                    event_type=entry.event_type,
                    occurred_at=entry.occurred_at,
                    title=entry.title,
                    description=entry.description,
                )
                for entry in timeline_entries
            ],
        )

        capsule.is_stale = False
        capsule.stale_reason = None
        capsule.last_refreshed_at = utcnow()
        capsule.updated_by = triggered_by
        await self._capsules.update(capsule)

        self._events.publish(
            CapsuleRefreshedEvent(
                capsule_id=capsule.id,
                workspace_id=workspace_id,
                expertise_count=len(expertise_insights),
                ownership_count=len(ownership_insights),
            )
        )
        await self._audit.record(
            AuditEventType.CAPSULE_REFRESHED,
            user_id=triggered_by,
            workspace_id=workspace_id,
            metadata={
                "capsule_id": str(capsule.id),
                "expertise_count": len(expertise_insights),
                "ownership_count": len(ownership_insights),
            },
        )
        return capsule

    async def mark_stale(
        self, capsule_id: uuid.UUID, *, workspace_id: uuid.UUID, reason: str
    ) -> None:
        capsule = await self._capsules.get_by_id(capsule_id)
        if capsule is None or capsule.workspace_id != workspace_id or capsule.is_stale:
            return
        capsule.is_stale = True
        capsule.stale_reason = reason
        await self._capsules.update(capsule)
        self._events.publish(
            CapsuleMarkedStaleEvent(
                capsule_id=capsule.id, workspace_id=workspace_id, reason=reason
            )
        )

    async def list_stale(
        self, *, workspace_id: uuid.UUID
    ) -> list[EmployeeKnowledgeCapsule]:
        return await self._capsules.list_stale(workspace_id=workspace_id)

    async def mark_stale_for_workspace(
        self, workspace_id: uuid.UUID, *, reason: str
    ) -> int:
        """CIS Phase 5 Prompt 3's Continuous Updates — the coarse,
        workspace-wide sweep
        cerebrum.application.capsules.continuous_updates.ContinuousUpdateListener's
        drained pending workspaces feed into (see that module's
        docstring for why this is workspace-scoped rather than
        capsule-pinpointed). Returns how many capsules were newly
        marked stale.
        """
        page = await self.list_in_workspace(
            workspace_id=workspace_id,
            pagination=Pagination(page=1, page_size=_SEARCH_PAGE_SIZE),
        )
        marked = 0
        for capsule in page.items:
            if capsule.is_stale:
                continue
            await self.mark_stale(capsule.id, workspace_id=workspace_id, reason=reason)
            marked += 1
        return marked

    async def list_evidence(
        self, capsule_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[CapsuleEvidenceRecord]:
        capsule = await self.get(capsule_id, workspace_id=workspace_id)
        return await self._evidence.list_by_capsule(capsule.id)

    async def list_timeline(
        self, capsule_id: uuid.UUID, *, workspace_id: uuid.UUID, pagination: Pagination
    ) -> Page[CapsuleTimelineEvent]:
        capsule = await self.get(capsule_id, workspace_id=workspace_id)
        return await self._timeline.list_by_capsule(capsule.id, pagination=pagination)

    async def delete(
        self, capsule_id: uuid.UUID, *, workspace_id: uuid.UUID, deleted_by: uuid.UUID
    ) -> None:
        capsule = await self.get(capsule_id, workspace_id=workspace_id)
        await self._capsules.soft_delete(capsule.id)
        await self._audit.record(
            AuditEventType.CAPSULE_DELETED,
            user_id=deleted_by,
            workspace_id=workspace_id,
            metadata={"capsule_id": str(capsule.id)},
        )

    async def list_in_workspace(
        self, *, workspace_id: uuid.UUID, pagination: Pagination
    ) -> Page[EmployeeKnowledgeCapsule]:
        return await self._capsules.list(
            pagination=pagination,
            filters=[
                FilterSpec(
                    field="workspace_id", operator=FilterOperator.EQ, value=workspace_id
                )
            ],
        )

    async def compare(
        self,
        user_id_a: uuid.UUID,
        user_id_b: uuid.UUID,
        *,
        workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        capsule_a = await self.get_for_user(user_id_a, workspace_id=workspace_id)
        capsule_b = await self.get_for_user(user_id_b, workspace_id=workspace_id)

        names_a = {item["canonical_name"] for item in capsule_a.expertise_map}
        names_b = {item["canonical_name"] for item in capsule_b.expertise_map}
        owned_a = {item["canonical_name"] for item in capsule_a.ownership_map}
        owned_b = {item["canonical_name"] for item in capsule_b.ownership_map}

        return {
            "user_id_a": str(user_id_a),
            "user_id_b": str(user_id_b),
            "shared_expertise": sorted(names_a & names_b),
            "unique_expertise_a": sorted(names_a - names_b),
            "unique_expertise_b": sorted(names_b - names_a),
            "shared_ownership": sorted(owned_a & owned_b),
            "unique_ownership_a": sorted(owned_a - owned_b),
            "unique_ownership_b": sorted(owned_b - owned_a),
        }

    async def expertise_search(
        self, *, workspace_id: uuid.UUID, query: str
    ) -> list[dict[str, Any]]:
        page = await self.list_in_workspace(
            workspace_id=workspace_id,
            pagination=Pagination(page=1, page_size=_SEARCH_PAGE_SIZE),
        )
        needle = query.strip().casefold()
        results: list[dict[str, Any]] = []
        for capsule in page.items:
            matches = [
                item
                for item in capsule.expertise_map
                if needle in item["canonical_name"].casefold()
            ]
            if matches:
                results.append(
                    {
                        "user_id": str(capsule.user_id),
                        "capsule_id": str(capsule.id),
                        "matches": sorted(
                            matches, key=lambda item: item["score"], reverse=True
                        ),
                    }
                )
        results.sort(
            key=lambda result: max(m["score"] for m in result["matches"]),
            reverse=True,
        )
        return results

    async def ownership_search(
        self, *, workspace_id: uuid.UUID, query: str
    ) -> list[dict[str, Any]]:
        page = await self.list_in_workspace(
            workspace_id=workspace_id,
            pagination=Pagination(page=1, page_size=_SEARCH_PAGE_SIZE),
        )
        needle = query.strip().casefold()
        results: list[dict[str, Any]] = []
        for capsule in page.items:
            matches = [
                item
                for item in capsule.ownership_map
                if needle in item["canonical_name"].casefold()
            ]
            if matches:
                results.append(
                    {
                        "user_id": str(capsule.user_id),
                        "capsule_id": str(capsule.id),
                        "matches": sorted(
                            matches, key=lambda item: item["score"], reverse=True
                        ),
                    }
                )
        results.sort(
            key=lambda result: max(m["score"] for m in result["matches"]),
            reverse=True,
        )
        return results

    async def organizational_knowledge_map(
        self, *, workspace_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        page = await self.list_in_workspace(
            workspace_id=workspace_id,
            pagination=Pagination(page=1, page_size=_SEARCH_PAGE_SIZE),
        )
        return [
            {
                "user_id": str(capsule.user_id),
                "capsule_id": str(capsule.id),
                "organizational_role": capsule.organizational_role,
                "top_expertise": sorted(
                    capsule.expertise_map, key=lambda item: item["score"], reverse=True
                )[:5],
                "top_ownership": sorted(
                    capsule.ownership_map, key=lambda item: item["score"], reverse=True
                )[:5],
                "is_stale": capsule.is_stale,
            }
            for capsule in page.items
        ]

    async def get_ai_capsule(
        self, capsule_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> dict[str, Any]:
        """CIS Phase 5 Prompt 3's AI Capsule: a structured,
        evidence-backed payload meant to be handed to
        cerebrum.application.ai.rag_service.RAGService by a caller —
        this method never calls an LLM itself, so nothing it returns is
        an unverified claim generated about a real person (see this
        module's docstring).
        """
        capsule = await self.get(capsule_id, workspace_id=workspace_id)
        timeline_page = await self._timeline.list_by_capsule(
            capsule.id, pagination=Pagination(page=1, page_size=20)
        )
        return {
            "capsule_id": str(capsule.id),
            "user_id": str(capsule.user_id),
            "expertise_map": capsule.expertise_map,
            "ownership_map": capsule.ownership_map,
            "dependency_graph": {
                "note": (
                    "Not materialized here — walk graph_references.person_entity_id "
                    "via RetrievalStrategy.GRAPH for live dependency traversal."
                )
            },
            "organizational_context": {
                "organizational_role": capsule.organizational_role,
                "responsibilities": capsule.responsibilities,
                "active_projects": capsule.active_projects,
                "technical_leadership": capsule.technical_leadership,
            },
            "active_work": capsule.active_projects,
            "historical_context": [
                {
                    "event_type": event.event_type,
                    "title": event.title,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in timeline_page.items
            ],
            "graph_references": {
                "person_entity_id": (
                    str(capsule.person_entity_id) if capsule.person_entity_id else None
                )
            },
            "retrieval_references": {
                "workspace_id": str(workspace_id),
                "suggested_strategy": "graph",
            },
        }

    async def _infer_collaboration(
        self, person_entity_id: uuid.UUID, *, workspace_id: uuid.UUID
    ) -> list[CollaborationInsight]:
        relationships = await self._relationships.list_for_entity(
            person_entity_id, workspace_id=workspace_id
        )
        collaboration_edges = [
            relationship
            for relationship in relationships
            if relationship.relationship_type == RelationshipType.COLLABORATION.value
        ]

        by_other: dict[uuid.UUID, list[Relationship]] = {}
        for edge in collaboration_edges:
            other_id = (
                edge.target_entity_id
                if edge.source_entity_id == person_entity_id
                else edge.source_entity_id
            )
            by_other.setdefault(other_id, []).append(edge)

        insights: list[CollaborationInsight] = []
        for other_id, edges in by_other.items():
            other = await self._entities.get(other_id, workspace_id=workspace_id)
            if other.entity_type != EntityType.PERSON.value:
                continue
            strength = round(sum(edge.confidence for edge in edges) / len(edges), 4)
            evidence = [
                EvidenceRef(
                    description=(
                        f"Collaboration relationship with '{other.canonical_name}'"
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
                CollaborationInsight(
                    entity_id=other.id,
                    canonical_name=other.canonical_name,
                    strength=strength,
                    evidence=evidence,
                )
            )
        insights.sort(key=lambda insight: insight.strength, reverse=True)
        return insights

    async def _identity_link_timestamp(self, capsule_id: uuid.UUID) -> datetime | None:
        records = await self._evidence.list_by_capsule_and_type(
            capsule_id, insight_type="identity_link"
        )
        if not records:
            return None
        return records[0].created_at

    async def _persist_evidence(
        self,
        capsule_id: uuid.UUID,
        insight_type: str,
        insight_key: str,
        reference: EvidenceRef,
    ) -> CapsuleEvidenceRecord:
        return await self._evidence.add(
            CapsuleEvidenceRecord(
                capsule_id=capsule_id,
                insight_type=insight_type,
                insight_key=insight_key,
                confidence=reference.confidence,
                description=reference.description,
                entity_id=reference.entity_id,
                relationship_id=reference.relationship_id,
                document_id=reference.document_id,
                connector_id=reference.connector_id,
                external_url=reference.external_url,
            )
        )
