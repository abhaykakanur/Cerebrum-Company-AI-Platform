# 81 — API Standards

## Purpose

This document defines the mechanical standards every Cerebrum API surface follows: Request Standards, Response Standards, Pagination, Filtering, Rate Limiting, API Versioning, and Observability. It elaborates FR-AP-006 from [20_Functional_Requirements.md](20_Functional_Requirements.md) and operationalizes [80_API_Architecture.md](80_API_Architecture.md)'s Consistent principle.

## Scope

This document covers cross-cutting request/response mechanics. It does not cover error-specific formatting (see [82_Error_Model.md](82_Error_Model.md)) or webhook-specific delivery mechanics (see [83_Webhook_Architecture.md](83_Webhook_Architecture.md)).

## Definitions

- **Correlation ID** — An identifier linking a client-side request to its corresponding server-side processing, distinct from the server-generated Request ID (a Correlation ID may be client-supplied to link related requests; a Request ID is always server-assigned).
- **Cursor Pagination** — A pagination approach using an opaque pointer to a specific position in a result set, rather than a numeric offset, remaining stable even as the underlying data changes between requests.

## Request Standards

Every request SHALL support:

| Element | Purpose |
|---|---|
| Authentication | Per [76_Authentication_Architecture.md](76_Authentication_Architecture.md) — the Access Token, validated before any other request processing. |
| Authorization | Per [77_Authorization_Model.md](77_Authorization_Model.md) — evaluated once the authenticated actor and target resource are known. |
| Correlation ID | Supports [38_Observability.md](38_Observability.md)'s Distributed Tracing when a client-side correlation identifier is provided, linked to the server's own trace context. |
| Tenant ID | Derived from the authenticated actor's Organization per [46_Multi_Tenancy.md](46_Multi_Tenancy.md), never client-supplied as an override (preventing a tenant-spoofing attempt via a manipulated header/parameter). |
| Workspace Context | Derived from the URL path per [80_API_Architecture.md](80_API_Architecture.md)'s hierarchy convention, or an explicit workspace-scoping parameter where the resource is not naturally nested. |
| Validation | DTO-level structural validation per [34_Architecture_Principles.md](34_Architecture_Principles.md)'s Application Layer Validation. |
| Tracing | Per [38_Observability.md](38_Observability.md)'s OpenTelemetry-based Distributed Tracing, initiated or propagated on every request. |

## Response Standards

Every response SHALL include:

| Field | Purpose |
|---|---|
| Status | The outcome (success/failure), redundant with but distinct from the HTTP status code — supports clients that inspect the body without separately parsing the HTTP status line. |
| Message | A human-readable summary of the outcome. |
| Timestamp | When the response was generated. |
| Request ID | The server-assigned identifier, correlating this response with server-side logs/traces per [38_Observability.md](38_Observability.md). |
| Version | The API version that served this request, confirming which version's contract applies even if the client's requested version differs due to redirection/negotiation (Deferred to Architecture for whether version negotiation is supported at all beyond the explicit URL version segment). |
| Data | The actual resource payload. |
| Pagination (if applicable) | Per the Pagination section below, present only for collection-returning endpoints. |
| Metadata | Any additional response-level context not part of the core Data payload (e.g., applied filters, result counts). |

## Error Model Cross-Reference

Error responses follow this same Response Standards envelope with `Status` indicating failure, plus the additional fields defined in [82_Error_Model.md](82_Error_Model.md) — this document does not duplicate that structure.

## HTTP Status Strategy

APIs SHALL use standard HTTP semantics: 2xx for success, 4xx for client errors, 5xx for server errors. Status codes SHALL NOT be overloaded (e.g., returning `200 OK` with an error indicated only in the body, or using a single generic `400` for every distinct client-error condition where a more specific code — `401`, `403`, `404`, `409`, `422`, `429` — applies). This directly supports API Consistency ([80_API_Architecture.md](80_API_Architecture.md)) and allows standard HTTP tooling (caches, proxies, monitoring) to reason correctly about API behavior without Cerebrum-specific knowledge.

## Pagination

Support:

| Type | Use |
|---|---|
| Offset Pagination | Simple page-number/page-size navigation, suitable for smaller, less-frequently-changing result sets. |
| Cursor Pagination | Per the definition above — required for large or frequently changing result sets (e.g., Search results, Audit Log queries) where Offset Pagination's instability under concurrent writes would cause skipped or duplicated results. |
| Configurable Page Size | Within a bounded range (see Maximum Limits). |
| Maximum Limits | A hard ceiling on page size, preventing a single request from requesting an unbounded result set — directly supporting API Abuse mitigation in [79_Threat_Model.md](79_Threat_Model.md). |

## Filtering

Support:

Field Filters, Date Filters, Metadata Filters, Sorting, Searching, Combined Filters.

These directly correspond to [71_Search_Pipeline.md](71_Search_Pipeline.md)'s thirteen Filtering dimensions where the API surface in question is search/collection-listing-oriented — this document establishes the API-mechanical support for filtering; [71_Search_Pipeline.md](71_Search_Pipeline.md) establishes which specific dimensions Enterprise Search exposes. "Combined Filters" specifically means multiple filter types may be applied in a single request (e.g., a Date Filter and a Metadata Filter together), combined with logical AND unless a filter syntax explicitly supports OR (Deferred to Architecture for filter-expression syntax).

## Rate Limiting

Support configurable rate limiting across the following five dimensions:

Per User, Per Workspace, Per Organization, Per API Key, Per IP.

**Binding rule:** Graceful throttling SHALL be preferred over abrupt failures. A client approaching its rate limit SHOULD receive an early signal (e.g., a `Retry-After` header or a rate-limit-remaining response header) before being outright rejected with a `429` status, and where architecturally feasible, request queuing/delay is preferred over immediate rejection for a client marginally over its limit — directly extending the same graceful-degradation philosophy already established for Connector retry handling ([68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)) and Search failure handling ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) to the API layer.

## API Versioning

Support:

| Element | Description |
|---|---|
| Major Versions | Breaking changes only ship in a new major version, per FR-AP-006. |
| Minor Versions | Backward-compatible additions (new optional fields, new endpoints) may increment a minor version without requiring client migration. |
| Backward Compatibility | A minor version increment SHALL NOT break an existing client integrated against the same major version. |
| Deprecation Policy | Per Open Question 36 in [40_Open_Questions.md](40_Open_Questions.md) — the specific deprecation window remains open, but the policy's existence (a defined window between deprecation notice and removal) is binding. |
| Migration Documentation | Every major version transition is accompanied by documentation describing required client changes — a Documented-principle ([80_API_Architecture.md](80_API_Architecture.md)) obligation specific to versioning transitions. |

## Observability

Every API SHALL expose:

Latency, Request Count, Error Rate, Success Rate, Rate Limit Metrics, Authentication Metrics, Authorization Metrics.

This directly extends [38_Observability.md](38_Observability.md)'s Metrics architecture with the API-layer-specific metric set — Authentication Metrics and Authorization Metrics in particular support [79_Threat_Model.md](79_Threat_Model.md)'s Broken Authentication/Broken Authorization detection by making anomalous authentication/authorization failure rates visible to the Monitoring Layer's degradation alerting (FR-MN-003).

## Responsibilities

- Every new API endpoint must implement the full Request and Response Standards envelope before release — a partial implementation (e.g., missing Request ID in responses) breaks the Consistency principle for every client relying on the standard shape.
- Rate Limiting's graceful-throttling preference must be verified during API implementation review, not merely assumed from the presence of a rate limiter.

## Constraints

- This document does not specify exact rate limit thresholds per dimension — Deferred to Architecture.
- This document does not specify the exact cursor-pagination token format — Deferred to Architecture.

## Future Considerations

- As API usage patterns are observed via the Observability metrics required here, rate limit thresholds and pagination defaults should be tuned from real traffic data rather than left at initial estimates indefinitely.

## Acceptance Criteria

- [ ] All seven Request Standards elements and eight Response Standards fields from the governing specification are defined.
- [ ] HTTP Status Strategy's "do not overload status codes" rule is stated as binding.
- [ ] All four Pagination elements, six Filtering types, five Rate Limiting dimensions, and five API Versioning elements from the governing specification are defined.
- [ ] All seven Observability metrics from the governing specification are defined and connected to [38_Observability.md](38_Observability.md) and [79_Threat_Model.md](79_Threat_Model.md).
