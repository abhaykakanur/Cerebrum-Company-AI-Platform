# 84 — Open Questions (CES Phase 0, Part 7)

## Purpose

This document records security- and API-architecture-specific ambiguities surfaced while writing [75_Security_Architecture.md](75_Security_Architecture.md) through [83_Webhook_Architecture.md](83_Webhook_Architecture.md). It extends, and does not replace, [11_Open_Questions.md](11_Open_Questions.md) (Part 1), [27_Open_Questions.md](27_Open_Questions.md) (Part 2), [40_Open_Questions.md](40_Open_Questions.md) (Part 3), [49_Open_Questions.md](49_Open_Questions.md) (Part 4), [64_Open_Questions.md](64_Open_Questions.md) (Part 5), and [74_Open_Questions.md](74_Open_Questions.md) (Part 6). Ambiguity is recorded here rather than resolved by assumption.

## Scope

This document covers ambiguities in security and API design left unresolved by documents 75–83. Numbering continues from [74_Open_Questions.md](74_Open_Questions.md) to maintain one unified backlog across all seven CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 93 | What is the Platform Owner role's specific access-grant mechanism — a standing role assignment, just-in-time elevation with time-bound expiry, or a break-glass procedure requiring dual approval? | [78_RBAC_Model.md](78_RBAC_Model.md) flags this as requiring resolution before general availability given its tension with tenant isolation, without specifying the mechanism. | 78 | Platform operations tooling, tenant-isolation guarantee strength. |
| 94 | What are the default Password Policy values (minimum length, complexity rules, expiration period, history depth)? | [76_Authentication_Architecture.md](76_Authentication_Architecture.md) defines the configurable elements without proposing defaults. | 76 | Authentication implementation, new-organization onboarding defaults. |
| 95 | What are the default Access Token and Refresh Token lifetimes? | [76_Authentication_Architecture.md](76_Authentication_Architecture.md)'s Token Strategy requires expiration without specifying durations, which directly affects the JWT Decision Rationale's exposure-window tradeoff. | 76 | Authentication implementation, security posture baseline. |
| 96 | What is the complete Resource Type × Action validity matrix — which of the sixteen Supported Actions apply to which of the seventeen Resource Types? | [77_Authorization_Model.md](77_Authorization_Model.md) establishes both enumerations without cross-defining valid combinations. | 77 | Authorization Service implementation, permission-assignment UI validation. |
| 97 | What specific, monitored condition triggers evaluation of the RBAC-to-ABAC migration named in [77_Authorization_Model.md](77_Authorization_Model.md)'s Decision Rationale? | The rationale states RBAC is sufficient for now without defining what "no longer sufficient" would concretely look like. | 77 | Long-term Authorization Service roadmap. |
| 98 | What is the specific URL convention for actions that do not map cleanly to standard HTTP methods (e.g., "archive," "approve")? | [80_API_Architecture.md](80_API_Architecture.md) proposes an illustrative sub-resource/action-noun pattern without committing to it as the binding convention. | 80 | API Domain implementation consistency. |
| 99 | Does the API support content negotiation or version negotiation beyond the mandatory URL version segment (e.g., an `Accept` header-based version override)? | [81_API_Standards.md](81_API_Standards.md)'s Response Standards mentions version negotiation as a possibility without resolving whether it is supported at all. | 81 | API Domain implementation, client integration patterns. |
| 100 | What filter-expression syntax supports Combined Filters, and does it support OR logic or only AND combination across filter types? | [81_API_Standards.md](81_API_Standards.md) defers the specific syntax while establishing that combination is required. | 81 | API query-parameter design, Enterprise Search filter UI. |
| 101 | What are the default Rate Limiting thresholds per dimension (per user, workspace, organization, API key, IP)? | [81_API_Standards.md](81_API_Standards.md) requires configurable limits without proposing defaults. | 81 | API Domain implementation, Brute Force/API Abuse mitigation baseline ([79_Threat_Model.md](79_Threat_Model.md)). |
| 102 | What cryptographic algorithm signs outbound webhook payloads, and what is the signature verification instruction format provided to subscribers? | [83_Webhook_Architecture.md](83_Webhook_Architecture.md) requires Signature Verification without specifying the algorithm (e.g., HMAC-SHA256) or documentation format. | 83 | Webhook Architecture implementation, subscriber integration documentation. |
| 103 | What are the specific retry backoff parameters and Dead Letter Queue retention for webhook delivery, and do they differ from the Connector Retry Engine's parameters (Open Question 83 in [74_Open_Questions.md](74_Open_Questions.md))? | [83_Webhook_Architecture.md](83_Webhook_Architecture.md) reuses the Connector retry pattern without confirming whether webhook-specific tuning is needed given the different failure profile (a subscriber's endpoint vs. a source system's API). | 83 | Webhook delivery reliability implementation. |
| 104 | Should the Error Code catalog be maintained as a formal, versioned registry (analogous to [22_Requirement_Catalog.md](22_Requirement_Catalog.md)) from the start, or grown organically and formalized later? | [82_Error_Model.md](82_Error_Model.md) proposes this as a future consideration without committing to timing. | 82 | API documentation tooling, client SDK generation readiness. |

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Question 93 (Platform Owner access mechanism) carries the highest security priority in this batch, given its direct bearing on the tenant-isolation guarantee that underpins the entire multi-tenant trust model.

## Constraints

- This list reflects ambiguities identifiable from the Part 7 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 75–83 rises to the level of a tracked open question here — routine, low-risk implementation latitude is intentionally not tracked.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the pattern in Parts 1–6's Open Questions documents) with a link to the governing ADR.
- With seven parts' worth of Open Questions now accumulated (104 total questions across [11](11_Open_Questions.md), [27](27_Open_Questions.md), [40](40_Open_Questions.md), [49](49_Open_Questions.md), [64](64_Open_Questions.md), [74](74_Open_Questions.md), and this document), the consolidated cross-part index recommended in [74_Open_Questions.md](74_Open_Questions.md)'s Future Considerations becomes increasingly warranted before architecture-implementation work begins.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific Part 7 document(s) it arose from.
- [ ] No question duplicates a question already recorded in [11_Open_Questions.md](11_Open_Questions.md), [27_Open_Questions.md](27_Open_Questions.md), [40_Open_Questions.md](40_Open_Questions.md), [49_Open_Questions.md](49_Open_Questions.md), [64_Open_Questions.md](64_Open_Questions.md), or [74_Open_Questions.md](74_Open_Questions.md) without adding security/API-architecture-level specificity.
