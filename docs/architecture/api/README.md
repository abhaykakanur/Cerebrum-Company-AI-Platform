# API Platform

The Enterprise API Platform & Developer Experience foundation (CIS Phase
1, Prompt 6): router framework, request validation, response
standardization, pagination/filtering/sorting, API versioning, OpenAPI
improvements, request context dependencies, serialization, the File
Foundation, the completed rate-limiting framework, and API metrics
hooks. Reusable platform only — no business endpoints. See each guide's
own scope note for specifics.

## Guides

| I want to... | Read |
|---|---|
| Understand the API's architectural principles and URL conventions | [api-architecture.md](api-architecture.md) |
| Understand how API versions are registered and deprecated | [versioning-guide.md](versioning-guide.md) |
| Find the right dependency for a new route (auth, pagination, rate limiting, ...) | [dependency-guide.md](dependency-guide.md) |
| Return a standardized response from a new endpoint | [response-guide.md](response-guide.md) |
| Validate a request's query/path/body parameters | [validation-guide.md](validation-guide.md) |
| See the full checklist a new endpoint must satisfy before release | [developer-api-standards.md](developer-api-standards.md) |

## What Exists

| Concern | Where |
|---|---|
| Router aggregation | `cerebrum.api.router`, `cerebrum.api.v1.router` |
| Response envelope | `cerebrum.api.schemas.envelope` (built by CIS Phase 1 Prompt 3) |
| Response builders (fills Request ID/Correlation ID/Version automatically) | `cerebrum.api.response_builder` |
| Serialization base + reusable serializers | `cerebrum.api.schemas.base` |
| Pagination/Filtering/Sorting query-param dependencies | `cerebrum.dependencies.pagination` |
| Pagination/Filtering/Sorting repository-layer contracts | `cerebrum.repositories.contracts` (built by CIS Phase 1 Prompt 4) |
| API Version Registry | `cerebrum.api.versions`, `cerebrum.api.version_routes` (`GET /api/versions`) |
| OpenAPI tags/operation IDs/error documentation | `cerebrum.core.metadata`, `cerebrum.api.openapi_responses` |
| Request Context dependencies (Tenant, Request ID, Correlation ID, Permissions) | `cerebrum.dependencies.request_context` |
| Current User / Current Workspace / RBAC dependencies | `cerebrum.dependencies.auth` (built by CIS Phase 1 Prompt 5) |
| File Foundation (upload/download/streaming/validation interfaces) | `cerebrum.infrastructure.storage.files` |
| General-purpose rate limiting (Per User/Tenant/API Key/Anonymous) | `cerebrum.dependencies.rate_limit` |
| Login-specific rate limiting | `cerebrum.dependencies.auth.enforce_login_rate_limit` (built by CIS Phase 1 Prompt 5) |
| API metrics (Latency, Request Count, Status Codes, Endpoint Usage, Response Size) | `cerebrum.middleware.metrics` |

## Non-Objectives

Explicitly out of scope for this milestone — see the CIS Phase 1 Prompt
6 prompt text: document ingestion, AI, RAG, knowledge graph, search,
chat, memory, analytics, connectors, business workflows. No business
endpoint or repository is added anywhere in this codebase by this
milestone — every example in these guides showing one (e.g.
`/documents`) is illustrative, for a future domain to actually build.
