"""``OrganizationalMemoryService``: CIS Phase 5 Prompt 3's
Organizational Timeline. Derives every entry purely from evidence
:class:`~cerebrum.application.capsules.expertise_inference_service.ExpertiseInferenceService`/
:class:`~cerebrum.application.capsules.ownership_inference_service.OwnershipInferenceService`
already produced during the same refresh pass — this service issues no
queries of its own, so a capsule's timeline can never diverge from what
its own expertise/ownership maps claim.
"""

from datetime import datetime

from cerebrum.application.capsules.dataclasses_ import (
    ExpertiseInsight,
    OwnershipInsight,
    TimelineEntry,
)


class OrganizationalMemoryService:
    def build_timeline(
        self,
        *,
        expertise_insights: list[ExpertiseInsight],
        ownership_insights: list[OwnershipInsight],
        linked_at: datetime | None = None,
    ) -> list[TimelineEntry]:
        entries: list[TimelineEntry] = []
        if linked_at is not None:
            entries.append(
                TimelineEntry(
                    event_type="identity_link",
                    occurred_at=linked_at,
                    title="Linked to knowledge-graph identity",
                    description=None,
                    evidence=None,
                )
            )

        for ownership_insight in ownership_insights:
            for reference in ownership_insight.evidence:
                if reference.occurred_at is None:
                    continue
                entries.append(
                    TimelineEntry(
                        event_type="ownership_change",
                        occurred_at=reference.occurred_at,
                        title=f"Ownership signal: {ownership_insight.canonical_name}",
                        description=reference.description,
                        evidence=reference,
                    )
                )

        for expertise_insight in expertise_insights:
            name = expertise_insight.canonical_name
            for reference in expertise_insight.evidence:
                if reference.occurred_at is None:
                    continue
                entries.append(
                    TimelineEntry(
                        event_type="contribution",
                        occurred_at=reference.occurred_at,
                        title=f"Contribution evidence: {name}",
                        description=reference.description,
                        evidence=reference,
                    )
                )

        entries.sort(key=lambda entry: entry.occurred_at, reverse=True)
        return entries
