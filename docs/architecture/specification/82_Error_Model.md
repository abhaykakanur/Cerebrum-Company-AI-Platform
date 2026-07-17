# 82 — Error Model

## Purpose

This document defines the standardized error response structure every Cerebrum API surface uses. It connects the API-facing error format to the error taxonomy already established in [38_Observability.md](38_Observability.md), ensuring a client-visible error and an internal error classification are two views of the same underlying event, not two disconnected concepts.

## Scope

This document covers the API-facing error response shape. It does not redefine the error taxonomy itself (Recoverable/Fatal, Validation/Security/Connector/AI/Storage/Search categories — see [38_Observability.md](38_Observability.md)).

## Definitions

- **Error Code** — A stable, machine-readable identifier for a specific error condition, distinct from the HTTP status code (which indicates the general error class) and the Message (which is human-readable).

## Standardized Error Fields

Every error response SHALL include:

| Field | Purpose |
|---|---|
| Error Code | A stable identifier (e.g., `PERMISSION_DENIED`, `VALIDATION_FAILED`) a client can programmatically branch on, distinct from the HTTP status which only conveys the general class. |
| Message | A human-readable description of what went wrong. |
| Details | Structured, error-specific additional context (e.g., which field failed validation and why), supporting the same fact/inference-style precision the AI Response Generation architecture requires ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)) — an error message should be as evidence-grounded and specific as an AI answer, not a generic catch-all string. |
| Request ID | Correlates the error with server-side logs and traces, per [81_API_Standards.md](81_API_Standards.md)'s Response Standards. |
| Timestamp | When the error occurred. |
| Suggested Resolution | Where determinable, a concrete next step for the client/user (e.g., "retry after refreshing your authentication token," "contact your workspace administrator to request access") — directly extending the Failure Handling philosophy already established in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) ("suggest corrective actions where appropriate") from the AI subsystem to every API surface. |

## Error Code Taxonomy Alignment

Error Codes SHALL be derivable from the [38_Observability.md](38_Observability.md) error taxonomy's categories, ensuring the API-facing Error Code and the internal error classification never diverge:

| API Error Code Family | Corresponds to [38_Observability.md](38_Observability.md) Category |
|---|---|
| `VALIDATION_*` | Validation Error |
| `PERMISSION_*`, `AUTHENTICATION_*` | Security Error |
| `CONNECTOR_*` | Connector Error |
| `AI_*` | AI Error |
| `STORAGE_*` | Storage Error |
| `SEARCH_*` | Search Error |

This alignment means a client debugging a `CONNECTOR_SYNC_TIMEOUT` Error Code can reliably expect the same underlying handling characteristics (transient, retryable) that [38_Observability.md](38_Observability.md)'s Connector Error category defines — the Error Model is not a separate, API-specific error design but the external-facing projection of the internal taxonomy already established.

## Security Error Disclosure

Per Open Question 19 in [40_Open_Questions.md](40_Open_Questions.md) (still open regarding the exact leakage policy), a Security Error's Message and Details fields SHALL NOT reveal information that would help an unauthorized actor infer the existence or nature of a resource they are not authorized to access — this document does not resolve the specific leakage policy but establishes that whatever policy is chosen applies uniformly to the Error Model's Message/Details fields, not only to successful-response payloads.

## Responsibilities

- Every new error condition introduced in a later phase must be assigned an Error Code from the appropriate taxonomy family before release — an error returned without a stable Error Code breaks client integrations that branch on it.
- Suggested Resolution should be populated wherever a concrete, safe-to-disclose next step exists; a generic "an error occurred, contact support" is acceptable only where no more specific guidance can be given without violating the Security Error Disclosure constraint above.

## Constraints

- This document does not enumerate every specific Error Code — Deferred to Architecture, growing incrementally as specific error conditions are implemented, each following the family-prefix convention above.
- This document does not resolve Open Question 19's specific leakage policy — it only establishes that the Error Model must comply with whatever policy is eventually decided.

## Future Considerations

- As the Error Code catalog grows, a machine-readable registry (analogous to [22_Requirement_Catalog.md](22_Requirement_Catalog.md)'s pattern for functional requirements) should be maintained so client SDK generation (per [80_API_Architecture.md](80_API_Architecture.md)'s Future SDK APIs category) can produce typed error handling.

## Acceptance Criteria

- [ ] All six Standardized Error fields from the governing specification are defined.
- [ ] Error Codes are explicitly aligned with the [38_Observability.md](38_Observability.md) error taxonomy, not an independent classification scheme.
- [ ] Security Error disclosure is addressed with an explicit connection to the still-open leakage-policy question rather than silently assumed.
