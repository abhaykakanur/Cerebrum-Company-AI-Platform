"""In-process result shapes CIS Phase 5 Prompt 3's inference services
return before
cerebrum.application.capsules.employee_knowledge_capsule_service.EmployeeKnowledgeCapsuleService
persists them as
:class:`~cerebrum.infrastructure.database.models.capsule_evidence.CapsuleEvidenceRecord`
rows and capsule JSON-map entries. Named ``dataclasses_`` (trailing
underscore) only to avoid shadowing the standard library ``dataclasses``
module within this package's own imports.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """One piece of support for an insight. Always traces back to a
    real, already-persisted knowledge-graph or connector-sync row —
    never a bare number: CIS Phase 5 Prompt 3's "No unsupported
    inference" requirement, expressed as a type every inference service
    must produce at least one of per insight.
    """

    description: str
    confidence: float
    relationship_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    connector_id: uuid.UUID | None = None
    external_url: str | None = None
    occurred_at: datetime | None = None
    """When the underlying evidence happened (e.g. a relationship's
    ``valid_from``/``created_at``) — what
    cerebrum.application.capsules.organizational_memory_service.OrganizationalMemoryService
    orders the Organizational Timeline by; ``None`` when the evidence
    has no meaningful point in time (e.g. an identity link uses its own
    occurrence instant instead).
    """


@dataclass(frozen=True, slots=True)
class ExpertiseInsight:
    entity_id: uuid.UUID
    canonical_name: str
    entity_type: str
    score: float
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OwnershipInsight:
    entity_id: uuid.UUID
    canonical_name: str
    entity_type: str
    ownership_category: str
    """One of ``repository``, ``service``, ``api``, ``database``,
    ``architecture``, ``general`` — read from the owned entity's
    ``custom_type_name``, falling back to ``general`` when unset.
    """
    share: float
    """This person's share (0.0-1.0) of the total ownership signal
    observed for the owned entity across every capsule in the
    workspace — the input
    cerebrum.application.capsules.risk_analysis_service.RiskAnalysisService's
    bus-factor/single-owner detection reads.
    """
    score: float
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CollaborationInsight:
    entity_id: uuid.UUID
    canonical_name: str
    strength: float
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    event_type: str
    occurred_at: datetime
    title: str
    description: str | None
    evidence: EvidenceRef | None


@dataclass(frozen=True, slots=True)
class SuccessorPlan:
    capsule_id: uuid.UUID
    critical_repositories: list[dict[str, Any]]
    key_collaborators: list[dict[str, Any]]
    learning_sequence: list[dict[str, Any]]
    recommended_reading: list[dict[str, Any]]
    open_work: list[dict[str, Any]]
    immediate_priorities: list[str]


@dataclass(frozen=True, slots=True)
class OwnerShare:
    person_entity_id: uuid.UUID
    canonical_name: str
    share: float


@dataclass(frozen=True, slots=True)
class BusFactorResult:
    entity_id: uuid.UUID
    canonical_name: str
    bus_factor: int
    owners: list[OwnerShare]
    risk_level: str
    """One of ``critical``, ``high``, ``medium``, ``low`` — see
    cerebrum.application.capsules.risk_analysis_service's module
    docstring for the exact thresholds.
    """


@dataclass(frozen=True, slots=True)
class CoverageReport:
    workspace_id: uuid.UUID
    total_owned_entities: int
    covered_entities: int
    coverage_score: float
    single_owner_entities: list[BusFactorResult]
