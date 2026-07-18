# Multi-Tenancy Guide

How Cerebrum resolves tenant and workspace context on every
authenticated request, and why cross-tenant access is prevented by
construction rather than by an explicit check that could be forgotten.

## Organization Is The Tenant Boundary

Every `User` belongs to exactly one `Organization` — that's the tenant.
`Organization.id` is embedded directly in the access token's `org_id`
claim at login (`cerebrum.infrastructure.security.jwt.TokenService`), so
resolving "which tenant is this request for" never requires a database
round-trip.

`Workspace` is a unit *within* an organization — an organization can
have many. Unlike `org_id`, **`workspace_id` is not embedded in the
token.** A user's set of workspace memberships can change without
forcing re-authentication, and which workspace a given request concerns
is a property of the request (a URL segment or header), not of the
user's identity.

## Request-Scoped Context

Every request's `cerebrum.middleware.context.RequestContext` (bound by
`RequestContextMiddleware`, populated after
`cerebrum.middleware.authentication.AuthenticationMiddleware` resolves
identity — see `cerebrum.middleware.registry`'s pipeline order) carries:

| Field | Source | Validated here? |
|---|---|---|
| `tenant_id` | Access token's `org_id` claim | Yes — token signature verified by `AuthenticationMiddleware` |
| `authenticated_user_id` | Access token's `sub` claim | Yes |
| `workspace_id` | `X-Workspace-ID` request header | **No — raw passthrough** |

`workspace_id` is intentionally unvalidated at the middleware layer —
validating "does this user actually belong to this workspace" requires
a database query, and `RequestContextMiddleware` runs for *every*
request (including ones with no workspace concept, like `/health`).
Pushing that query into every request unconditionally would be wasteful
and wrong for routes that don't need it.

## Where Validation Actually Happens

`cerebrum.dependencies.auth.get_current_workspace_id` reads
`RequestContext.workspace_id`, requires it to be present and a valid
UUID (422 otherwise), and hands it to whichever service needs it. The
service itself — most commonly
`cerebrum.application.auth.authorization_service.AuthorizationService`
via `require_permission` (see [rbac-guide.md](rbac-guide.md)) — is what
actually proves membership, by querying for a
`WorkspaceMembership` row. No membership row, no access — see this
guide's next section for why that's sufficient on its own.

## Why Cross-Tenant Access Is Prevented "By Design"

CIS Phase 1 Prompt 5 asks specifically for this, not just "an org check
somewhere." The property this codebase relies on:
`RoleRepository.get_permission_codes_for_membership` joins
`WorkspaceMembership → Role → RolePermission → Permission` filtered on
`(user_id, workspace_id)`. If no `WorkspaceMembership` row exists for
that exact pair, the join returns nothing — an **empty permission set**,
not an error, not a partial result. There is no separate "and also
check the workspace's organization matches the user's organization"
condition to write, get wrong, or forget in a future query. Cross-tenant
access isn't blocked; it's unreachable, because the only path to a
non-empty permission set requires a membership row a tenant boundary
violation could never have created.

`apps/backend/tests/unit/test_tenant_isolation.py` verifies this
directly, including the specific case a naive implementation could get
wrong: a `Permission.code` is a global string
(`"documents:read"` isn't itself scoped to an organization) —
`test_identical_permission_code_does_not_leak_across_organizations`
proves that two organizations independently granting the *same code
string* to their own users doesn't let one leak into the other.

## Trusted Proxy Support

`RequestContext.client_ip` (used for audit logging and rate limiting)
resolves through `X-Forwarded-For` only when the directly-connecting
peer is in `SECURITY_TRUSTED_PROXIES` (default: loopback only) — see
`cerebrum.middleware.request_context.RequestContextMiddleware._resolve_client_ip`.
An untrusted caller cannot spoof its own IP by sending a forged header.
