# 80 — API Architecture

## Purpose

This document defines the eight binding API Architecture Principles, the seven API Categories, and URL Conventions governing every Cerebrum API surface. It elaborates FR-AP-001 through FR-AP-006 from [20_Functional_Requirements.md](20_Functional_Requirements.md) and the API Domain architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Scope

This document covers API-wide architectural principles, surface categorization, and URL structure. It does not cover request/response payload standards (see [81_API_Standards.md](81_API_Standards.md)), error formatting (see [82_Error_Model.md](82_Error_Model.md)), or webhooks (see [83_Webhook_Architecture.md](83_Webhook_Architecture.md)).

## Definitions

- **Idempotent** — An operation that produces the same result regardless of how many times it is executed with the same input (e.g., a `DELETE` on an already-deleted resource is a no-op, not an error).
- **Resource-Oriented** — An API design style where URLs identify resources (nouns) and HTTP methods express the action (verb), as opposed to encoding actions into the URL path.

## API Architecture Principles

APIs SHALL be:

| Principle | Meaning |
|---|---|
| RESTful | Resource-oriented, using standard HTTP methods and status semantics — see Decision Rationale below for why REST over GraphQL in V1.0. |
| Versioned | Per FR-AP-006 and this document's URL Conventions. |
| Stateless | No server-side session state is required to interpret a request beyond the Authentication Token itself — see Decision Rationale below. |
| Idempotent where appropriate | `PUT`, `DELETE`, and other naturally idempotent operations are implemented idempotently; `POST` (resource creation) is not idempotent by HTTP semantics and is not forced to be, consistent with standard REST practice. |
| Consistent | The same conventions (naming, pagination, error shape) apply across every API Category below — a client learning one Cerebrum API surface's conventions can predict another's. |
| Documented | Every API surface has complete, current documentation — a Frontend/DevEx concern whose existence this architecture mandates without specifying the documentation tooling. |
| Observable | Per [81_API_Standards.md](81_API_Standards.md)'s Observability section. |
| Secure | Per [75_Security_Architecture.md](75_Security_Architecture.md) and [79_Threat_Model.md](79_Threat_Model.md) — every API principle in this document operates within, not instead of, the security architecture already established. |

### Decision Rationale: Why REST Over GraphQL for V1.0

REST is adopted for Version 1.0 over GraphQL for three reasons: (1) REST's resource-oriented model maps directly onto the Application Layer's existing command/query handler structure ([34_Architecture_Principles.md](34_Architecture_Principles.md)) without requiring a separate schema-stitching or resolver layer, keeping the API Domain's translation responsibility (request DTO ↔ application service ↔ response DTO, per [35_Domain_Architecture.md](35_Domain_Architecture.md)) simple and directly traceable to a single application service per endpoint; (2) REST's per-resource caching semantics (via standard HTTP caching headers) are simpler to reason about and operate than GraphQL's typically-POST-only, harder-to-cache request model, which matters given the Search Response and Retrieval performance targets ([39_Performance_Targets.md](39_Performance_Targets.md)); (3) Simple architecture over unnecessary complexity ([04_Project_Principles.md](04_Project_Principles.md)) — GraphQL's primary advantage (client-specified, flexible query shapes reducing over/under-fetching) is most valuable for complex, deeply nested, client-driven UIs; Cerebrum's initial API consumers (its own Frontend Layer and enterprise integration partners) are adequately served by REST's more predictable, more easily documented and versioned contract. GraphQL remains a future option — see [12_Future_Expansion.md](12_Future_Expansion.md)'s Future Expansion pattern — should client-side query flexibility needs outgrow REST's fit, and FR-AP-001's Future Expansion note already names this explicitly.

### Decision Rationale: Why Stateless APIs

Statelessness — no server-side session state beyond the Authentication Token — is required for Horizontal Scaling ([39_Performance_Targets.md](39_Performance_Targets.md)): a stateful API would require session affinity (routing a client's every request to the same backend instance) or a shared session store lookup on every request, either of which works against the Backend Layer's stateless, horizontally-scaled deployment model already established in [39_Performance_Targets.md](39_Performance_Targets.md)'s Horizontal Scaling strategy. This is the same rationale underlying the JWT Decision Rationale in [76_Authentication_Architecture.md](76_Authentication_Architecture.md) — both decisions serve the same architectural goal of avoiding a scaling bottleneck at the authentication/session layer.

## API Categories

| Category | Purpose | Requirement Traceability |
|---|---|---|
| Public APIs | External, authenticated integration access equivalent to primary interface capability. | FR-AP-001 |
| Authenticated APIs | The general category any non-public, credential-requiring API belongs to — a superset classification Public, Administrative, and Connector APIs all fall within (every Cerebrum API requires authentication per [75_Security_Architecture.md](75_Security_Architecture.md); "Authenticated APIs" as a named category here refers to first-party, non-public-marketed integration surfaces distinct from the officially documented Public API). | Implicit across FR-AP-001–004 |
| Administrative APIs | Programmatic access to Administration Domain capability. | FR-AP-003 |
| Internal APIs | Service-to-service, in-process (in V1.0's Modular Monolith) contracts between domains. | FR-AP-002 |
| Connector APIs | The interface new Connector Plugins integrate through. | FR-AP-004, [66_Connector_SDK.md](66_Connector_SDK.md) |
| Webhook APIs | Outbound event delivery. | FR-AP-005, [83_Webhook_Architecture.md](83_Webhook_Architecture.md) |
| Future SDK APIs | Anticipated client SDKs (language-specific libraries wrapping the Public API) — not built in V1.0, but the Public API's REST/versioning discipline is designed to make such SDKs straightforward to generate or hand-write later. | New — consistent with [12_Future_Expansion.md](12_Future_Expansion.md)'s extensibility pattern |

## URL Conventions

- **Base path:** `/api/v1/` — the version segment is mandatory on every request, never defaulted, directly implementing FR-AP-006's explicit version identifier requirement.
- **Resource-oriented naming:** URLs identify resources, not actions (e.g., `/api/v1/documents/{id}`, not `/api/v1/getDocument`).
- **Plural resources:** Collection endpoints use plural nouns (`/documents`, not `/document`).
- **No verbs in endpoint paths where possible:** Actions are expressed via HTTP method (`POST /documents` to create, `DELETE /documents/{id}` to delete) rather than a verb in the path; where an action does not map cleanly to a standard HTTP method (e.g., "archive" is not simply `DELETE`), a sub-resource or action-noun pattern is preferred over a verb (e.g., `POST /documents/{id}/archive-actions`, Deferred to Architecture for the exact convention) over a bare verb path like `/archiveDocument`.
- **Consistent path hierarchy:** Nested resources reflect their ownership hierarchy from [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md) (e.g., `/api/v1/workspaces/{workspaceId}/documents`), consistent with [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s scoping — a request's tenant/workspace scope is derivable from its path, not solely from a header, wherever the resource is naturally workspace-scoped.

## Responsibilities

- Every new API endpoint introduced in a later phase must comply with all eight API Architecture Principles and the URL Conventions before release — a non-compliant endpoint (e.g., a verb-in-path action, an unversioned route) is a review-blocking finding.
- The REST-over-GraphQL and Stateless API decisions are binding architectural decisions, not preferences; a later phase introducing GraphQL as a parallel primary API or a stateful session model requires an ADR per [09_Governance.md](09_Governance.md).

## Constraints

- This document does not specify exact endpoint paths, request/response schemas, or OpenAPI specification content — Deferred to Architecture.
- "Future SDK APIs" names an anticipated category without committing to specific languages or a delivery timeline.

## Future Considerations

- If GraphQL is introduced later per this document's Decision Rationale's stated conditions, it should be added as a new API Category alongside, not replacing, REST — consistent with the general pattern of extending rather than redesigning established architecture.

## Acceptance Criteria

- [ ] All eight API Architecture Principles from the governing specification are defined, with REST-over-GraphQL and Stateless API Decision Rationales included.
- [ ] All seven API Categories from the governing specification are defined and traced to FR-AP requirements where applicable.
- [ ] URL Conventions address versioning, resource-orientation, plural naming, verb avoidance, and path hierarchy consistency.
