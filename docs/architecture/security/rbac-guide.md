# RBAC Guide

Role-Based Access Control framework. No business permission is seeded
anywhere in this codebase — see CIS Phase 1 Prompt 5's "No business
permissions yet" scope. This guide is for the domain that defines the
first one.

## The Model

```
User ──< WorkspaceMembership >── Workspace
              │
              ▼
             Role ──< RolePermission >── Permission
```

A `WorkspaceMembership` grants one user one `Role` within one
`Workspace` — at most one row per `(user, workspace)` pair (a unique
constraint enforces this; a user needing different access in different
workspaces gets a different `Role` per membership, not multiple roles in
one workspace). A `Role` holds zero or more `Permission`s via
`RolePermission`. `Permission.code` is a plain string (e.g.
`"documents:read"`) — this framework doesn't interpret it; a future
domain defines what codes exist and what they gate.

**Permission resolution is structurally tenant-safe** — see
[multi-tenancy-guide.md](multi-tenancy-guide.md) and
`apps/backend/tests/unit/test_tenant_isolation.py`: the query underneath
`has_permission`/`require_permission` joins through
`WorkspaceMembership`, so a user with no membership row in a workspace
gets an empty permission set for it, full stop — there's no separate
"does this workspace belong to this user's org" check to forget to add.

## Protecting a Route

```python
from fastapi import APIRouter, Depends
from cerebrum.dependencies.auth import require_permission

router = APIRouter()

@router.get("/documents", dependencies=[Depends(require_permission("documents:read"))])
async def list_documents(...):
    ...
```

`require_permission(code)` is a dependency **factory** — each call
returns a fresh closure bound to `code`. Under the hood it depends on:

1. `CurrentIdentityDep` — who is asking (401 if unauthenticated).
2. `WorkspaceIdDep` — which workspace, from the `X-Workspace-ID` header
   (422 if absent/malformed — see [multi-tenancy-guide.md](multi-tenancy-guide.md)).
3. `AuthorizationServiceDep` — the actual check, raising
   `PermissionDeniedException` (403) if the membership/role chain
   doesn't include `code`.

A denial is recorded as a `PERMISSION_DENIED` audit event automatically
— see `cerebrum.application.auth.authorization_service.AuthorizationService.require_permission`.

## Checking a Permission Without Protecting a Whole Route

```python
from cerebrum.dependencies.auth import AuthorizationServiceDep, CurrentIdentityDep, WorkspaceIdDep

@router.get("/documents/{id}")
async def get_document(
    identity: CurrentIdentityDep, workspace_id: WorkspaceIdDep, authz: AuthorizationServiceDep, ...
):
    can_delete = await authz.has_permission(
        user_id=identity.user_id, workspace_id=workspace_id, permission_code="documents:delete"
    )
    ...  # e.g. include a "can_delete" field in the response, not a hard 403
```

`has_permission` returns `bool` and never raises or audits — use it for
conditional UI/response shaping; use `require_permission` (or the
`Depends(require_permission(...))` route-level form) when the action
must actually be blocked.

## System-Wide Roles

`Role.organization_id` is nullable — `NULL` marks a system-wide role
available to every organization (e.g. a future platform-admin role);
non-`NULL` marks an organization-defined custom role. No system-wide
role is created by this milestone.

## Testing a Protected Route

`apps/backend/tests/unit/test_auth_api.py::TestRoutePermissionProtection`
mounts a throwaway route with `Depends(require_permission(...))` to
verify the mechanism end-to-end over HTTP — a real domain route follows
the identical pattern shown in "Protecting a Route" above.
