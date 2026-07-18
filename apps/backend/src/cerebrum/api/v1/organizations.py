"""The Organization API surface — CIS Phase 2 Prompt 1. Operates only on
the caller's own organization (from
:data:`~cerebrum.dependencies.request_context.TenantIdDep`, the access
token's claim) — no route accepts an arbitrary organization ID; see
cerebrum.application.knowledge.organization_service's docstring for why.
No fine-grained RBAC permission check beyond authentication: this is an
organization-wide (not workspace-scoped) operation, and CIS Phase 1
Prompt 5's RBAC framework is inherently workspace-scoped (permission
resolution joins through ``WorkspaceMembership`` — see
docs/architecture/security/rbac-guide.md). A system-wide/org-admin role
distinction is Deferred to Architecture (``Role.organization_id`` is
already nullable in anticipation of it — see
cerebrum.infrastructure.database.models.role.Role's docstring).
"""

from fastapi import APIRouter

from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES
from cerebrum.api.response_builder import build_success_response
from cerebrum.api.schemas.envelope import SuccessResponse
from cerebrum.api.schemas.knowledge import (
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from cerebrum.dependencies.auth import CurrentUserDep
from cerebrum.dependencies.knowledge import OrganizationServiceDep
from cerebrum.dependencies.request_context import TenantIdDep
from cerebrum.dependencies.settings import SettingsDep

router = APIRouter(
    prefix="/organizations", tags=["Organizations"], responses=STANDARD_ERROR_RESPONSES
)


@router.get("/me", response_model=SuccessResponse[OrganizationResponse])
async def get_my_organization(
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    organizations: OrganizationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[OrganizationResponse]:
    """The caller's own organization."""
    organization = await organizations.get(tenant_id)
    return build_success_response(
        OrganizationResponse.model_validate(organization), settings=settings
    )


@router.patch("/me", response_model=SuccessResponse[OrganizationResponse])
async def rename_my_organization(
    body: OrganizationUpdateRequest,
    _current_user: CurrentUserDep,
    tenant_id: TenantIdDep,
    organizations: OrganizationServiceDep,
    settings: SettingsDep,
) -> SuccessResponse[OrganizationResponse]:
    organization = await organizations.rename(tenant_id, name=body.name)
    return build_success_response(
        OrganizationResponse.model_validate(organization), settings=settings
    )
