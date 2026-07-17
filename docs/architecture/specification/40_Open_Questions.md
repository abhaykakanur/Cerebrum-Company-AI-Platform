# 40 — Open Questions (CES Phase 0, Part 3)

## Purpose

This document records architecture-level ambiguities and "Deferred to Architecture" points surfaced while writing [30_System_Architecture.md](30_System_Architecture.md) through [39_Performance_Targets.md](39_Performance_Targets.md). It extends, and does not replace, [11_Open_Questions.md](11_Open_Questions.md) (Part 1) and [27_Open_Questions.md](27_Open_Questions.md) (Part 2). Per the Architecture Quality Checklist's instruction, any architectural decision that was uncertain during Part 3 authoring is recorded here rather than resolved by assumption.

## Scope

This document covers architecture-specific ambiguities: technology-selection details deferred within an otherwise-decided category, operational parameters left unset, and cross-cutting mechanisms whose design is acknowledged but not specified. Numbering continues from [27_Open_Questions.md](27_Open_Questions.md) to maintain one unified backlog across all three CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 38 | Which multi-tenancy isolation model does PostgreSQL use — schema-per-tenant, row-level security with a shared schema, or database-per-tenant? | [30_System_Architecture.md](30_System_Architecture.md)'s Security Overview requires structural tenant isolation but defers the specific mechanism; this decision also directly drives Search and Vector sharding strategy in [39_Performance_Targets.md](39_Performance_Targets.md). Sharpens Open Question 3 in [11_Open_Questions.md](11_Open_Questions.md) to a concrete architectural choice. | 30, 39 | Persistence Layer implementation, Search/Vector scaling strategy. |
| 39 | Which secrets-management backend is used in production — a cloud provider's native secrets manager, HashiCorp Vault, or another product? | [37_Configuration_Strategy.md](37_Configuration_Strategy.md) requires the Security Domain's `GetSecret` port to have a production-grade adapter but defers product selection. | 37 | Infrastructure Layer implementation, deployment provisioning. |
| 40 | Is OpenSearch or Elasticsearch the final search technology, and what is the licensing review outcome at architecture-implementation time? | [32_Technology_Stack.md](32_Technology_Stack.md) prefers OpenSearch by default but explicitly defers final selection to a licensing review closer to implementation, since license terms may have changed. | 32 | Enterprise Search and Retrieval Domain infrastructure adapters. |
| 41 | Is the search/vector index partitioned per-organization or shared with tenant-filtered queries? | [39_Performance_Targets.md](39_Performance_Targets.md)'s Search Scaling and Vector Scaling strategies both depend on this and explicitly defer it to the same decision as Open Question 38. | 39 | Enterprise Search, Retrieval Domain infrastructure, capacity planning. |
| 42 | What is the LLM/embedding provider fallback policy when the primary provider fails or times out — retry the same provider, fail over to a secondary provider, or return an explicit AI Error to the user? | [38_Observability.md](38_Observability.md)'s AI Error handling rule requires a policy to exist but does not specify it; the choice has direct cost, latency, and answer-consistency implications. | 38 | AI Layer infrastructure adapters, Open Question 10 in [11_Open_Questions.md](11_Open_Questions.md) (model sourcing). |
| 43 | What is the cache-invalidation mechanism for the Authorization Layer's permission-decision cache, given the correctness sensitivity of ever serving a stale "allow" decision after a permission is revoked? | [31_Component_Architecture.md](31_Component_Architecture.md) and [39_Performance_Targets.md](39_Performance_Targets.md) both flag this as a first-class performance concern without specifying the invalidation approach (e.g., short TTL vs. active invalidation on every permission change). | 31, 39 | Authorization Layer infrastructure, Security review. |
| 44 | What are the specific retry-count, backoff-multiplier, and DLQ-retention parameters for each Background Processing Task category? | [36_Background_Processing.md](36_Background_Processing.md) requires per-category retry/DLQ policy to exist but defers the concrete parameters, which likely differ meaningfully between, e.g., an LLM-provider-rate-limit retry and a database-connection retry. | 36 | Background Processing Layer implementation. |
| 45 | Is chat response streaming delivered via Server-Sent Events or WebSocket? | [31_Component_Architecture.md](31_Component_Architecture.md) names this as the mechanism for AI Layer token-by-token delivery but defers the specific protocol choice. | 31 | Frontend Layer and API Domain implementation. |
| 46 | Which Kubernetes manifest tooling is used — raw manifests, Kustomize, or Helm? | [33_Directory_Structure.md](33_Directory_Structure.md) reserves a `deployment/kubernetes/` location but defers the templating/packaging tool choice. | 33 | Deployment/DevOps tooling setup. |
| 47 | What Python dependency/packaging tool (Poetry, uv, pip-tools) and monorepo tooling (if any, e.g., Nx, Turborepo for the frontend/backend split) are used? | [33_Directory_Structure.md](33_Directory_Structure.md) explicitly defers this. | 33 | Local development setup, CI pipeline definition. |
| 48 | What concrete, monitored metric and threshold triggers the Celery-to-Temporal background-processing migration named in [32_Technology_Stack.md](32_Technology_Stack.md)? | The migration decision itself is made (Celery for V1.0, Temporal as the identified future target), but the trigger condition is described qualitatively ("pipeline complexity or scale outgrows Celery's capabilities") rather than as a monitored threshold. | 32, 36 | Long-term Background Processing Layer roadmap. |
| 49 | What is the distributed trace sampling strategy once 100% trace capture becomes cost-prohibitive at scale, and does it preserve full capture for Security Errors and AI Reasoning traces as recommended? | [38_Observability.md](38_Observability.md) flags this as a future consideration without committing to a sampling algorithm or rate. | 38 | Monitoring Layer implementation, observability cost management. |
| 50 | What are the log and metric retention periods, and do they differ from the Audit Domain's own retention policy (which is governed separately by FR-KS-004 and legal/compliance requirements)? | [38_Observability.md](38_Observability.md) explicitly defers retention periods; general operational logs plausibly warrant a shorter retention window than audit records, but this is not decided. | 38 | Observability infrastructure cost planning, compliance alignment with Open Question 11 in [11_Open_Questions.md](11_Open_Questions.md). |
| 51 | What are the per-connector circuit-breaker thresholds that prevent one degraded source system's failures from consuming a disproportionate share of Background Processing Layer worker capacity? | [39_Performance_Targets.md](39_Performance_Targets.md)'s Connector Sync Reliability target implies this protection is needed but does not specify threshold values. | 39, 36 | Connector Layer resilience implementation. |
| 52 | What staleness/lag tolerance is acceptable for PostgreSQL read replicas serving Analytics and Audit read queries, and does any Audit read path require strict (non-replica) consistency given its compliance role? | [39_Performance_Targets.md](39_Performance_Targets.md) proposes read replicas for these query paths without addressing whether Audit's compliance-evidentiary role tolerates eventual consistency. | 39 | Persistence Layer read-path routing, compliance review. |
| 53 | What production object-storage target does the MinIO S3-API-compatible adapter point to — a specific cloud provider's object storage service, a self-hosted MinIO cluster, or another S3-compatible product? | [32_Technology_Stack.md](32_Technology_Stack.md) deliberately keeps the adapter S3-API-generic but does not commit to the production target. | 32 | Infrastructure Layer provisioning, data residency (Open Question 3 dependency). |
| 54 | Does the local-development secrets adapter's environment-gating (preventing its accidental selection in staging/production) rely on a build-time check, a runtime environment assertion, or both? | [37_Configuration_Strategy.md](37_Configuration_Strategy.md) requires this safeguard to exist but does not specify its enforcement mechanism, which is itself a security-relevant implementation detail. | 37 | Security review, CI/CD pipeline design. |

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Questions here that are prerequisites for other questions (e.g., Open Question 38 gates Open Question 41) should be resolved in dependency order during architecture-implementation kickoff.

## Constraints

- This list reflects ambiguities identifiable from the Part 3 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 30–39 rises to the level of a tracked open question here — routine, low-risk implementation latitude (e.g., exact class naming) is intentionally not tracked as an open question.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring [11_Open_Questions.md](11_Open_Questions.md) and [27_Open_Questions.md](27_Open_Questions.md)) with a link to the governing ADR.
- Given the number of Part 3 open questions that trace back to the Part 1 multi-tenancy question (Open Question 3), that question should be treated as the highest-priority item to resolve before architecture-implementation work begins in earnest.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific Part 3 document(s) it arose from.
- [ ] No question duplicates a question already recorded in [11_Open_Questions.md](11_Open_Questions.md) or [27_Open_Questions.md](27_Open_Questions.md) without adding architecture-level specificity.
