"""Reusable Request Context dependencies (CIS Phase 1 Prompt 6): Request
ID, Correlation ID, and Current Tenant. Current User and Current
Workspace already exist as
:data:`~cerebrum.dependencies.auth.CurrentUserDep`/:data:`~cerebrum.dependencies.auth.WorkspaceIdDep`;
Current Permissions is added here since it composes
:data:`~cerebrum.dependencies.auth.AuthorizationServiceDep`, already
defined in that module.

Distinct from cerebrum.middleware.request_context, which builds and
binds the underlying :class:`~cerebrum.middleware.context.RequestContext`
once per request — these are the typed, individually-injectable
accessors a route depends on instead of reading the ambient context
object directly, per docs/architecture/dependency-injection.md.
"""

import uuid
from typing import Annotated

from fastapi import Depends

from cerebrum.dependencies.auth import (
    AuthorizationServiceDep,
    CurrentIdentityDep,
    WorkspaceIdDep,
)
from cerebrum.middleware.context import get_current_request_context
from cerebrum.shared.errors.exceptions import ValidationException


def get_request_id() -> str:
    context = get_current_request_context()
    if context is None:
        raise ValidationException("No active request context.")
    return context.request_id


def get_correlation_id() -> str | None:
    context = get_current_request_context()
    return context.correlation_id if context is not None else None


RequestIdDep = Annotated[str, Depends(get_request_id)]
CorrelationIdDep = Annotated[str | None, Depends(get_correlation_id)]


def get_current_tenant_id(identity: CurrentIdentityDep) -> uuid.UUID:
    """The authenticated actor's Organization — see
    docs/architecture/specification/81_API_Standards.md's Request
    Standards ("Tenant ID ... never client-supplied as an override").
    Derived solely from the validated access token's ``organization_id``
    claim via :class:`~cerebrum.middleware.context.AuthIdentity`, never
    from a header or query parameter — see
    docs/architecture/security/multi-tenancy-guide.md.
    """
    return identity.organization_id


TenantIdDep = Annotated[uuid.UUID, Depends(get_current_tenant_id)]


async def get_current_permissions(
    identity: CurrentIdentityDep,
    workspace_id: WorkspaceIdDep,
    authorization_service: AuthorizationServiceDep,
) -> frozenset[str]:
    """Every permission code the current identity holds in the current
    workspace — see
    cerebrum.application.auth.authorization_service.AuthorizationService.get_permissions.
    A route that only needs to gate access to one permission should
    prefer :func:`~cerebrum.dependencies.auth.require_permission`
    instead; this dependency is for a route that needs to know the full
    set (e.g. to shape its own response).
    """
    return await authorization_service.get_permissions(
        user_id=identity.user_id, workspace_id=workspace_id
    )


CurrentPermissionsDep = Annotated[frozenset[str], Depends(get_current_permissions)]
