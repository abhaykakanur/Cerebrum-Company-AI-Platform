# Validation Guide

## Body Validation

Pydantic request models, validated by FastAPI before the route body
runs — the existing pattern (`RefreshRequest`, `LogoutRequest` in
`cerebrum.api.schemas.auth`). A validation failure raises
`RequestValidationError`, handled by
`cerebrum.core.exception_handlers.handle_validation_error` into a `422`
with one `ErrorDetail` per invalid field — no route needs its own
try/except for this.

## Path and Query Parameters

Standard FastAPI: type-annotate the route function's parameters
(`id: uuid.UUID`, `active: bool = Query(default=True)`). An invalid UUID
or an out-of-range value is rejected the same way as a malformed body —
`422`, same envelope.

## Pagination, Filtering, Sorting

See [dependency-guide.md](dependency-guide.md)'s Pagination, Sorting,
Filtering section — `PaginationDep`/`SortDep`/`FilterDep` from
`cerebrum.dependencies.pagination` cover this; do not hand-roll
`page`/`page_size`/`sort`/`filter` query parameters on a new route.

## Headers

`X-Workspace-ID` (`WorkspaceIdDep`), `X-Correlation-ID` (read via
`CorrelationIdDep`), `X-API-Key` (read by
`cerebrum.dependencies.rate_limit.rate_limit_per_api_key` and, for
actual key validation, `cerebrum.application.auth.api_key_service.APIKeyService.validate`)
are the headers this platform already defines meaning for. A new
feature-specific header should follow the same `X-`-prefixed,
`PascalCase`-hyphenated convention.

## Enums

A Pydantic/Python `Enum`/`StrEnum` field is validated automatically —
an invalid value is a structural validation failure (`422`), not
something a route checks manually. See `cerebrum.repositories.contracts.FilterOperator`
and `cerebrum.api.versions.VersionStatus` for the existing convention
(`StrEnum`, not a bare `str` with manual value-checking).

## Business-Rule Validation

Structural validation (this document's concern) is distinct from
business-rule validation (e.g. "this document is already archived") —
the latter belongs to the application service, not the API layer, and
raises `cerebrum.shared.errors.exceptions.ValidationException` directly
rather than through a Pydantic model. See
docs/architecture/coding-guidelines.md and
[34_Architecture_Principles.md](../specification/34_Architecture_Principles.md)'s
Application Layer Validation.
