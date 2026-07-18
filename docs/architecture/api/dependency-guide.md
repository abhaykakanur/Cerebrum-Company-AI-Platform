# API Dependency Guide

Every reusable `Depends()` a route can take, by concern. See
docs/architecture/dependency-injection.md for the general DI pattern
this codebase follows (FastAPI-native `Depends()`, no custom container).

## Pagination, Sorting, Filtering

`cerebrum.dependencies.pagination` translates raw query strings into the
datastore-agnostic contracts `cerebrum.repositories.contracts` defines
(CIS Phase 1 Prompt 4) — no repository or business query lives in this
module.

```python
from cerebrum.dependencies.pagination import FilterDep, PaginationDep, SortDep

@router.get("/documents")
async def list_documents(
    pagination: PaginationDep, sort: SortDep, filters: FilterDep, session: DbSessionDep
):
    page = await DocumentRepository(session).list(pagination=pagination, sort=sort, filters=filters)
    ...
```

| Query string | Resolves to |
|---|---|
| `?page=2&page_size=20` | `Pagination(page=2, page_size=20)` (1–500 page_size, enforced by both FastAPI validation and `Pagination.__post_init__`) |
| `?sort=name,-created_at` | `[SortSpec("name", ASC), SortSpec("created_at", DESC)]` — leading `-` means descending |
| `?filter=status:eq:active&filter=created_at:gte:2024-01-01` | `[FilterSpec("status", EQ, "active"), FilterSpec("created_at", GTE, "2024-01-01")]` — repeatable, combined with AND |

`filter`'s `in` operator takes a comma-separated value list:
`?filter=status:in:active,pending` → `FilterSpec("status", IN, ["active", "pending"])`.

A malformed filter (wrong shape, unknown operator) raises
`ValidationException` (422), caught by the standard exception handler —
no route needs its own try/except.

## Request Context

`cerebrum.dependencies.request_context` and `cerebrum.dependencies.auth`
together cover every ambient value a route commonly needs:

| Dependency | Type | Source |
|---|---|---|
| `CurrentIdentityDep` (auth) | `AuthIdentity` | Access token's claims, no DB hit |
| `CurrentUserDep` (auth) | `User` | Loads the full row |
| `WorkspaceIdDep` (auth) | `uuid.UUID` | `X-Workspace-ID` header |
| `TenantIdDep` (request_context) | `uuid.UUID` | Access token's `organization_id` claim — **never** a header, per [81_API_Standards.md](../specification/81_API_Standards.md)'s Request Standards |
| `RequestIdDep` (request_context) | `str` | The bound `RequestContext` |
| `CorrelationIdDep` (request_context) | `str \| None` | The bound `RequestContext` |
| `CurrentPermissionsDep` (request_context) | `frozenset[str]` | RBAC — every permission code held in the current workspace |

Use `CurrentPermissionsDep` when a route needs the *full set* (e.g. to
shape which fields/actions its response exposes); use
`Depends(require_permission("code"))` (see
[rbac-guide.md](../security/rbac-guide.md)) when the route should be
flatly blocked for lacking one specific permission.

## Rate Limiting

`cerebrum.dependencies.rate_limit` completes the Rate Limiting
Foundation CIS Phase 1 Prompt 5 built for login specifically. Four
dependency *factories*, each returning a fresh closure — mirroring
`require_permission`'s shape:

```python
from cerebrum.dependencies.rate_limit import rate_limit_per_user

@router.post("/documents", dependencies=[Depends(rate_limit_per_user(max_attempts=30, window_seconds=60))])
async def create_document(...): ...
```

| Factory | Dimension | Keyed by | Requires |
|---|---|---|---|
| `rate_limit_per_user` | Per User | `identity.user_id` | Authentication |
| `rate_limit_per_tenant` | Per Tenant | `TenantIdDep` | Authentication |
| `rate_limit_per_api_key` | Per API Key | hash of `X-API-Key` header | Nothing — no-ops if the header is absent |
| `rate_limit_anonymous` | Per IP | resolved client IP (Trusted Proxy Support aware) | Nothing |

Omit `max_attempts`/`window_seconds` to use
`SecuritySettings.api_rate_limit_requests`/`api_rate_limit_window_seconds`
(defaults: 120 requests / 60 seconds). Every dimension fails open — logs
a warning and allows the request — when Redis is unreachable, matching
`enforce_login_rate_limit`'s rationale: basic route availability must
not become conditional on a cache being up.

Per Workspace (the fifth dimension in
[81_API_Standards.md](../specification/81_API_Standards.md)) is Deferred
to the first workspace-scoped route that needs it.

## File Foundation

`cerebrum.infrastructure.storage.files` defines `FileUploader`/`FileDownloader`
Protocol ports (no concrete adapter exists yet — Deferred to the first
feature that uploads/downloads a file) and `validate_file`/`FileValidationPolicy`
for structural validation:

```python
from cerebrum.infrastructure.storage.files import FileValidationPolicy, validate_file

_DOCUMENT_POLICY = FileValidationPolicy(
    max_size_bytes=100 * 1024 * 1024,
    allowed_content_types=frozenset({"application/pdf", "text/plain"}),
)

validate_file(filename=upload.filename, content_type=upload.content_type, size_bytes=size, policy=_DOCUMENT_POLICY)
```

## Response Building

See [response-guide.md](response-guide.md) for
`cerebrum.api.response_builder`.
