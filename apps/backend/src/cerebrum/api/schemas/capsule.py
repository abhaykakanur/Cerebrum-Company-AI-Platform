"""Request/response schemas for CIS Phase 5 Prompt 3's Employee
Knowledge Capsule API. Every response model inherits
:class:`~cerebrum.api.schemas.base.APIModel` — see
cerebrum.api.schemas.workflow's identical docstring precedent.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from cerebrum.api.schemas.base import APIModel

# --- Requests -----------------------------------------------------------------


class CreateCapsuleRequest(APIModel):
    user_id: uuid.UUID


class LinkPersonEntityRequest(APIModel):
    entity_id: uuid.UUID


class UpdateCapsuleProfileRequest(APIModel):
    organizational_role: str | None = Field(default=None, max_length=255)
    responsibilities: list[str] | None = None


# --- Responses ------------------------------------------------------------


class CapsuleResponse(APIModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    person_entity_id: uuid.UUID | None
    organizational_role: str | None
    responsibilities: list[str]
    expertise_map: list[dict[str, Any]]
    ownership_map: list[dict[str, Any]]
    active_projects: list[dict[str, Any]]
    collaboration_network: list[dict[str, Any]]
    technical_leadership: list[dict[str, Any]]
    is_stale: bool
    stale_reason: str | None
    last_refreshed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CapsuleTimelineEventResponse(APIModel):
    id: uuid.UUID
    event_type: str
    occurred_at: datetime
    title: str
    description: str | None


class CapsuleComparisonResponse(APIModel):
    user_id_a: str
    user_id_b: str
    shared_expertise: list[str]
    unique_expertise_a: list[str]
    unique_expertise_b: list[str]
    shared_ownership: list[str]
    unique_ownership_a: list[str]
    unique_ownership_b: list[str]


class ExpertiseSearchResultResponse(APIModel):
    user_id: str
    capsule_id: str
    matches: list[dict[str, Any]]


class OwnershipSearchResultResponse(APIModel):
    user_id: str
    capsule_id: str
    matches: list[dict[str, Any]]


class OrganizationalKnowledgeMapEntryResponse(APIModel):
    user_id: str
    capsule_id: str
    organizational_role: str | None
    top_expertise: list[dict[str, Any]]
    top_ownership: list[dict[str, Any]]
    is_stale: bool


class SuccessorPlanResponse(APIModel):
    capsule_id: uuid.UUID
    critical_repositories: list[dict[str, Any]]
    key_collaborators: list[dict[str, Any]]
    learning_sequence: list[dict[str, Any]]
    recommended_reading: list[dict[str, Any]]
    open_work: list[dict[str, Any]]
    immediate_priorities: list[str]


class OwnerShareResponse(APIModel):
    person_entity_id: uuid.UUID
    canonical_name: str
    share: float


class BusFactorResponse(APIModel):
    entity_id: uuid.UUID
    canonical_name: str
    bus_factor: int
    owners: list[OwnerShareResponse]
    risk_level: str


class CoverageReportResponse(APIModel):
    workspace_id: uuid.UUID
    total_owned_entities: int
    covered_entities: int
    coverage_score: float
    single_owner_entities: list[BusFactorResponse]
