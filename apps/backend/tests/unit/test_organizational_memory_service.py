"""Proves CIS Phase 5 Prompt 3's Organizational Timeline
(``OrganizationalMemoryService``): timeline entries are derived purely
from already-computed expertise/ownership evidence, in reverse
chronological order, and every entry traces back to a real
:class:`~cerebrum.application.capsules.dataclasses_.EvidenceRef`.
"""

import uuid
from datetime import timedelta

import pytest

from cerebrum.application.capsules.dataclasses_ import (
    EvidenceRef,
    ExpertiseInsight,
    OwnershipInsight,
)
from cerebrum.application.capsules.organizational_memory_service import (
    OrganizationalMemoryService,
)
from cerebrum.utils.clock import utcnow

pytestmark = pytest.mark.unit


def test_build_timeline_includes_identity_link_entry() -> None:
    service = OrganizationalMemoryService()
    linked_at = utcnow()

    entries = service.build_timeline(
        expertise_insights=[], ownership_insights=[], linked_at=linked_at
    )

    assert len(entries) == 1
    assert entries[0].event_type == "identity_link"
    assert entries[0].occurred_at == linked_at


def test_build_timeline_orders_entries_reverse_chronologically() -> None:
    service = OrganizationalMemoryService()
    now = utcnow()
    older_evidence = EvidenceRef(
        description="older", confidence=0.6, occurred_at=now - timedelta(days=5)
    )
    newer_evidence = EvidenceRef(description="newer", confidence=0.9, occurred_at=now)
    ownership_insights = [
        OwnershipInsight(
            entity_id=uuid.uuid4(),
            canonical_name="acme/widgets",
            entity_type="custom",
            ownership_category="repository",
            share=1.0,
            score=0.8,
            evidence=[older_evidence],
        )
    ]
    expertise_insights = [
        ExpertiseInsight(
            entity_id=uuid.uuid4(),
            canonical_name="Kubernetes",
            entity_type="technology",
            score=0.7,
            evidence=[newer_evidence],
        )
    ]

    entries = service.build_timeline(
        expertise_insights=expertise_insights, ownership_insights=ownership_insights
    )

    assert [entry.event_type for entry in entries] == [
        "contribution",
        "ownership_change",
    ]
    assert entries[0].occurred_at == now
    assert entries[1].occurred_at == now - timedelta(days=5)


def test_build_timeline_skips_evidence_without_a_timestamp() -> None:
    service = OrganizationalMemoryService()
    undated_evidence = EvidenceRef(description="undated", confidence=0.5)
    expertise_insights = [
        ExpertiseInsight(
            entity_id=uuid.uuid4(),
            canonical_name="Kubernetes",
            entity_type="technology",
            score=0.5,
            evidence=[undated_evidence],
        )
    ]

    entries = service.build_timeline(
        expertise_insights=expertise_insights, ownership_insights=[]
    )

    assert entries == []
