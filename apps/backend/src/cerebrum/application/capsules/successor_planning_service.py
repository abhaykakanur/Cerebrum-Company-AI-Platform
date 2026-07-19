"""``SuccessorPlanningService``: CIS Phase 5 Prompt 3's Successor
Assistant. Pure computation over an already-refreshed
:class:`~cerebrum.infrastructure.database.models.capsule.EmployeeKnowledgeCapsule`'s
persisted maps and its
:class:`~cerebrum.infrastructure.database.models.capsule_evidence.CapsuleEvidenceRecord`
rows — issues no new knowledge-graph queries itself, so a plan can
never recommend anything the capsule's own evidence doesn't already
support.
"""

import uuid
from typing import Any

from cerebrum.application.capsules.dataclasses_ import SuccessorPlan
from cerebrum.infrastructure.database.models.capsule import EmployeeKnowledgeCapsule
from cerebrum.infrastructure.database.models.capsule_evidence import (
    CapsuleEvidenceRecord,
)
from cerebrum.infrastructure.database.models.capsule_timeline_event import (
    CapsuleTimelineEvent,
)

_TOP_N = 10
_CRITICAL_OWNERSHIP_CATEGORIES = frozenset(
    {"repository", "service", "api", "database", "architecture"}
)


class SuccessorPlanningService:
    def generate_plan(
        self,
        capsule: EmployeeKnowledgeCapsule,
        *,
        evidence_records: list[CapsuleEvidenceRecord],
        recent_timeline: list[CapsuleTimelineEvent],
    ) -> SuccessorPlan:
        ownership = sorted(
            capsule.ownership_map, key=lambda item: item["score"], reverse=True
        )
        critical_repositories = [
            item
            for item in ownership
            if item.get("ownership_category") in _CRITICAL_OWNERSHIP_CATEGORIES
        ][:_TOP_N]
        key_collaborators = sorted(
            capsule.collaboration_network,
            key=lambda item: item["strength"],
            reverse=True,
        )[:_TOP_N]
        learning_sequence = ownership[:_TOP_N]
        recommended_reading = _distinct_reading_material(evidence_records)[:_TOP_N]
        open_work = [
            {
                "event_type": event.event_type,
                "title": event.title,
                "occurred_at": event.occurred_at.isoformat(),
            }
            for event in recent_timeline[:_TOP_N]
        ]
        immediate_priorities = [
            f"Review ownership of '{item['canonical_name']}' "
            f"({item['ownership_category']})"
            for item in critical_repositories[:3]
        ]

        return SuccessorPlan(
            capsule_id=capsule.id,
            critical_repositories=critical_repositories,
            key_collaborators=key_collaborators,
            learning_sequence=learning_sequence,
            recommended_reading=recommended_reading,
            open_work=open_work,
            immediate_priorities=immediate_priorities,
        )


def _distinct_reading_material(
    evidence_records: list[CapsuleEvidenceRecord],
) -> list[dict[str, Any]]:
    relevant = [
        record
        for record in evidence_records
        if record.insight_type in {"ownership", "expertise"}
        and (record.document_id is not None or record.external_url is not None)
    ]
    relevant.sort(key=lambda record: record.confidence, reverse=True)

    seen: set[tuple[uuid.UUID | None, str | None]] = set()
    reading_material: list[dict[str, Any]] = []
    for record in relevant:
        key = (record.document_id, record.external_url)
        if key in seen:
            continue
        seen.add(key)
        reading_material.append(
            {
                "insight_key": record.insight_key,
                "document_id": str(record.document_id) if record.document_id else None,
                "external_url": record.external_url,
                "description": record.description,
                "confidence": record.confidence,
            }
        )
    return reading_material
