"""The Employee Knowledge Capsule API surface — CIS Phase 5 Prompt 3's
Digital Organizational Twin endpoints, built entirely on
:class:`~cerebrum.application.capsules.employee_knowledge_capsule_service.EmployeeKnowledgeCapsuleService`/
:class:`~cerebrum.application.capsules.risk_analysis_service.RiskAnalysisService`/
:class:`~cerebrum.application.capsules.successor_planning_service.SuccessorPlanningService`
(see cerebrum.application.capsules's package docstring).

``"capsules:write"`` gates every mutating route (create/link/update-
profile/refresh/delete); ``"capsules:read"`` gates read-only routes —
mirroring cerebrum.api.v1.workflows's identical read/write permission
split. Tenant/Workspace Isolation is inherited structurally: every
route resolves ``workspace_id`` from ``WorkspaceIdDep`` and every
service call is scoped by it. **HR-sensitive filtering** is enforced
structurally, not by a redaction layer: nothing in
:class:`~cerebrum.infrastructure.database.models.capsule.EmployeeKnowledgeCapsule`
stores personal/private information beyond professional, evidence-
backed facts (role, expertise, ownership, collaboration) — there is no
sensitive field to filter, the same "excluded by construction"
reasoning
cerebrum.application.workflows.workflow_run_service.WorkflowRunService's
module docstring gives for why it never exposes a generic secrets root.
**Evidence Verification** is likewise structural — see
cerebrum.infrastructure.database.models.capsule_evidence.CapsuleEvidenceRecord's
docstring. **Audit logging** happens inside the service layer, not
here — every read that discloses a capsule's contents records
``CAPSULE_ACCESSED``.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import (
    build_collection_response,
    build_success_response,
)
from cerebrum.api.schemas.capsule import (
    BusFactorResponse,
    CapsuleComparisonResponse,
    CapsuleResponse,
    CapsuleTimelineEventResponse,
    CoverageReportResponse,
    CreateCapsuleRequest,
    ExpertiseSearchResultResponse,
    LinkPersonEntityRequest,
    OrganizationalKnowledgeMapEntryResponse,
    OwnershipSearchResultResponse,
    SuccessorPlanResponse,
    UpdateCapsuleProfileRequest,
)
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.dependencies.auth import (
    CurrentUserDep,
    WorkspaceIdDep,
    require_permission,
)
from cerebrum.dependencies.capsules import (
    EmployeeKnowledgeCapsuleServiceDep,
    RiskAnalysisServiceDep,
    SuccessorPlanningServiceDep,
)
from cerebrum.dependencies.settings import SettingsDep
from cerebrum.repositories.contracts import Pagination, map_page

router = APIRouter(
    prefix="/capsules",
    tags=["Employee Knowledge Capsules"],
    responses=STANDARD_ERROR_RESPONSES,
)

_write = Depends(require_permission("capsules:write"))
_read = Depends(require_permission("capsules:read"))


@router.post(
    "",
    response_model=SuccessResponse[CapsuleResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write],
)
async def create_capsule(
    body: CreateCapsuleRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CapsuleResponse]:
    capsule = await capsules.get_or_create_for_user(
        body.user_id,
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    return build_success_response(
        CapsuleResponse.model_validate(capsule), settings=settings
    )


@router.get(
    "", response_model=SuccessResponse[list[CapsuleResponse]], dependencies=[_read]
)
async def list_capsules(
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[CapsuleResponse]]:
    page_result = await capsules.list_in_workspace(
        workspace_id=workspace_id, pagination=Pagination(page=page, page_size=page_size)
    )
    return build_collection_response(
        map_page(page_result, CapsuleResponse.model_validate), settings=settings
    )


@router.get(
    "/compare",
    response_model=SuccessResponse[CapsuleComparisonResponse],
    dependencies=[_read],
)
async def compare_capsules(
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
    user_id_a: Annotated[uuid.UUID, Query()],
    user_id_b: Annotated[uuid.UUID, Query()],
) -> SuccessResponse[CapsuleComparisonResponse]:
    comparison = await capsules.compare(user_id_a, user_id_b, workspace_id=workspace_id)
    return build_success_response(
        CapsuleComparisonResponse.model_validate(comparison), settings=settings
    )


@router.get(
    "/search/expertise",
    response_model=SuccessResponse[list[ExpertiseSearchResultResponse]],
    dependencies=[_read],
)
async def search_expertise(
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
    query: Annotated[str, Query(min_length=1)],
) -> SuccessResponse[list[ExpertiseSearchResultResponse]]:
    results = await capsules.expertise_search(workspace_id=workspace_id, query=query)
    return build_success_response(
        [ExpertiseSearchResultResponse.model_validate(r) for r in results],
        settings=settings,
    )


@router.get(
    "/search/ownership",
    response_model=SuccessResponse[list[OwnershipSearchResultResponse]],
    dependencies=[_read],
)
async def search_ownership(
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
    query: Annotated[str, Query(min_length=1)],
) -> SuccessResponse[list[OwnershipSearchResultResponse]]:
    results = await capsules.ownership_search(workspace_id=workspace_id, query=query)
    return build_success_response(
        [OwnershipSearchResultResponse.model_validate(r) for r in results],
        settings=settings,
    )


@router.get(
    "/organizational-knowledge-map",
    response_model=SuccessResponse[list[OrganizationalKnowledgeMapEntryResponse]],
    dependencies=[_read],
)
async def organizational_knowledge_map(
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[list[OrganizationalKnowledgeMapEntryResponse]]:
    entries = await capsules.organizational_knowledge_map(workspace_id=workspace_id)
    return build_success_response(
        [OrganizationalKnowledgeMapEntryResponse.model_validate(e) for e in entries],
        settings=settings,
    )


@router.get(
    "/risk/bus-factor/{entity_id}",
    response_model=SuccessResponse[BusFactorResponse],
    dependencies=[_read],
)
async def get_bus_factor(
    entity_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    risk: RiskAnalysisServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[BusFactorResponse]:
    result = await risk.bus_factor(entity_id, workspace_id=workspace_id)
    return build_success_response(
        BusFactorResponse.model_validate(result), settings=settings
    )


@router.get(
    "/risk/coverage",
    response_model=SuccessResponse[CoverageReportResponse],
    dependencies=[_read],
)
async def get_coverage_report(
    workspace_id: WorkspaceIdDep,
    risk: RiskAnalysisServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CoverageReportResponse]:
    report = await risk.coverage_report(workspace_id=workspace_id)
    return build_success_response(
        CoverageReportResponse.model_validate(report), settings=settings
    )


@router.get(
    "/risk/critical-dependencies",
    response_model=SuccessResponse[list[BusFactorResponse]],
    dependencies=[_read],
)
async def get_critical_dependencies(
    workspace_id: WorkspaceIdDep,
    risk: RiskAnalysisServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[list[BusFactorResponse]]:
    results = await risk.critical_dependencies(workspace_id=workspace_id)
    return build_success_response(
        [BusFactorResponse.model_validate(r) for r in results], settings=settings
    )


@router.get(
    "/{capsule_id}",
    response_model=SuccessResponse[CapsuleResponse],
    dependencies=[_read],
)
async def get_capsule(
    capsule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CapsuleResponse]:
    capsule = await capsules.get(
        capsule_id, workspace_id=workspace_id, accessed_by=current_user.id
    )
    return build_success_response(
        CapsuleResponse.model_validate(capsule), settings=settings
    )


@router.delete(
    "/{capsule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_write]
)
async def delete_capsule(
    capsule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
) -> None:
    await capsules.delete(
        capsule_id, workspace_id=workspace_id, deleted_by=current_user.id
    )


@router.post(
    "/{capsule_id}/link",
    response_model=SuccessResponse[CapsuleResponse],
    dependencies=[_write],
)
async def link_person_entity(
    capsule_id: uuid.UUID,
    body: LinkPersonEntityRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CapsuleResponse]:
    capsule = await capsules.link_person_entity(
        capsule_id, body.entity_id, workspace_id=workspace_id, linked_by=current_user.id
    )
    return build_success_response(
        CapsuleResponse.model_validate(capsule), settings=settings
    )


@router.patch(
    "/{capsule_id}/profile",
    response_model=SuccessResponse[CapsuleResponse],
    dependencies=[_write],
)
async def update_capsule_profile(
    capsule_id: uuid.UUID,
    body: UpdateCapsuleProfileRequest,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CapsuleResponse]:
    capsule = await capsules.update_profile(
        capsule_id,
        workspace_id=workspace_id,
        organizational_role=body.organizational_role,
        responsibilities=body.responsibilities,
        updated_by=current_user.id,
    )
    return build_success_response(
        CapsuleResponse.model_validate(capsule), settings=settings
    )


@router.post(
    "/{capsule_id}/refresh",
    response_model=SuccessResponse[CapsuleResponse],
    dependencies=[_write],
)
async def refresh_capsule(
    capsule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    current_user: CurrentUserDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[CapsuleResponse]:
    capsule = await capsules.refresh(
        capsule_id,
        workspace_id=workspace_id,
        organization_id=current_user.organization_id,
        triggered_by=current_user.id,
    )
    return build_success_response(
        CapsuleResponse.model_validate(capsule), settings=settings
    )


@router.get(
    "/{capsule_id}/timeline",
    response_model=SuccessResponse[list[CapsuleTimelineEventResponse]],
    dependencies=[_read],
)
async def get_capsule_timeline(
    capsule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessResponse[list[CapsuleTimelineEventResponse]]:
    page_result = await capsules.list_timeline(
        capsule_id,
        workspace_id=workspace_id,
        pagination=Pagination(page=page, page_size=page_size),
    )
    return build_collection_response(
        map_page(page_result, CapsuleTimelineEventResponse.model_validate),
        settings=settings,
    )


@router.get(
    "/{capsule_id}/ai-capsule",
    response_model=SuccessResponse[dict[str, Any]],
    dependencies=[_read],
)
async def get_ai_capsule(
    capsule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[dict[str, Any]]:
    payload = await capsules.get_ai_capsule(capsule_id, workspace_id=workspace_id)
    return build_success_response(payload, settings=settings)


@router.get(
    "/{capsule_id}/successor-plan",
    response_model=SuccessResponse[SuccessorPlanResponse],
    dependencies=[_read],
)
async def get_successor_plan(
    capsule_id: uuid.UUID,
    workspace_id: WorkspaceIdDep,
    capsules: EmployeeKnowledgeCapsuleServiceDep,
    successor_planner: SuccessorPlanningServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[SuccessorPlanResponse]:
    capsule = await capsules.get(capsule_id, workspace_id=workspace_id)
    evidence_records = await capsules.list_evidence(
        capsule_id, workspace_id=workspace_id
    )
    timeline_page = await capsules.list_timeline(
        capsule_id,
        workspace_id=workspace_id,
        pagination=Pagination(page=1, page_size=20),
    )
    plan = successor_planner.generate_plan(
        capsule, evidence_records=evidence_records, recent_timeline=timeline_page.items
    )
    return build_success_response(
        SuccessorPlanResponse.model_validate(plan), settings=settings
    )
