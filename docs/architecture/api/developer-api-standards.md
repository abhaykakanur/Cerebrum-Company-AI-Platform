# Developer API Standards

The checklist a new endpoint must satisfy before release — CIS Phase 1
Prompt 6's Responsibilities section: "Every new API endpoint introduced
in a later phase must comply with all eight API Architecture Principles
and the URL Conventions before release — a non-compliant endpoint ... is
a review-blocking finding."

## Checklist

- [ ] **URL**: resource-oriented, plural collection noun, no verb in the
      path, mounted under `/api/v1` (or the current version's prefix) —
      see [api-architecture.md](api-architecture.md).
- [ ] **Router**: `APIRouter(tags=[...], responses=STANDARD_ERROR_RESPONSES)`,
      included from `cerebrum.api.v1.router` — see
      `cerebrum.api.v1.auth`'s pattern.
- [ ] **Tag registered**: add the new tag's description to
      `cerebrum.core.metadata.OPENAPI_TAGS` — an undocumented tag is a
      review-blocking finding under this same checklist.
- [ ] **Response envelope**: uses `cerebrum.api.response_builder`, per
      [response-guide.md](response-guide.md) — unless the endpoint has a
      specific, documented reason not to (the auth/health precedent).
- [ ] **Pagination/Filtering/Sorting**: a collection endpoint uses
      `PaginationDep`/`SortDep`/`FilterDep`, not hand-rolled query
      parameters.
- [ ] **Authentication/Authorization**: `CurrentUserDep` or
      `Depends(require_permission("..."))` as appropriate — no route is
      unauthenticated without a documented reason (health, versions,
      login are the existing exceptions).
- [ ] **Rate limiting**: a mutating or expensive endpoint takes at least
      one `cerebrum.dependencies.rate_limit` dimension.
- [ ] **Error documentation**: inherits `STANDARD_ERROR_RESPONSES` from
      its router; add any endpoint-specific status code
      (`responses={409: {...}}` on the route decorator) on top.
- [ ] **Docstring**: the route function's docstring is its OpenAPI
      operation description — write one, not a placeholder.
- [ ] **Business logic**: none in the route function — it translates
      request → application service call → response, per
      docs/architecture/dependency-rules.md.
- [ ] **Tests**: request validation, the success path, and every
      documented error path (401/403/404/422/429 as applicable).

## HTTP Status Discipline

Per [81_API_Standards.md](../specification/81_API_Standards.md)'s HTTP
Status Strategy: never `200` with an error only in the body, never a
generic `400` where `401`/`403`/`404`/`409`/`422`/`429` applies. Every
`cerebrum.shared.errors.base.PlatformException` subclass already carries
its correct `http_status` — raise the right exception type rather than
constructing a response with an explicit status code.

## What "Foundation, Not Business Logic" Means Here

Every module this milestone ships (`cerebrum.dependencies.pagination`,
`cerebrum.api.response_builder`, `cerebrum.api.versions`,
`cerebrum.dependencies.request_context`,
`cerebrum.infrastructure.storage.files`,
`cerebrum.dependencies.rate_limit`, `cerebrum.middleware.metrics`) is
generic — parameterized by field names, permission codes, or settings a
future domain supplies, never by a specific business concept. None of
it queries a business table, defines a business permission code, or
implements a business validation rule; see each module's own docstring
for its specific non-objective.
