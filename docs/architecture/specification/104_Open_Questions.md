# 104 — Open Questions (CES Phase 0, Part 9)

## Purpose

This document records DevOps-, testing-, and engineering-standards-specific ambiguities surfaced while writing [95_DevOps_Architecture.md](95_DevOps_Architecture.md) through [103_Engineering_Guidelines.md](103_Engineering_Guidelines.md). It extends, and does not replace, the Open Questions documents from Parts 1–8. Ambiguity is recorded here rather than resolved by assumption.

## Scope

This document covers ambiguities in DevOps, testing, and engineering-standards design left unresolved by documents 95–103. Numbering continues from [94_Open_Questions.md](94_Open_Questions.md) to maintain one unified backlog across all nine CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 117 | What triggering cadence applies to End-to-End, Performance, and AI Evaluation tests within the CI/CD pipeline — every merge to `main`, a scheduled nightly run, or a pre-release gate only? | [97_CICD_Architecture.md](97_CICD_Architecture.md) and [98_Testing_Strategy.md](98_Testing_Strategy.md) both defer this given the higher cost/time of these test types relative to Unit/Integration Tests. | 97, 98 | CI/CD pipeline implementation, test infrastructure cost planning. |
| 118 | Is the Deployment Approval pipeline stage a human sign-off, an automated policy gate, or both, and does this vary by target environment (Staging vs. Production)? | [97_CICD_Architecture.md](97_CICD_Architecture.md) names the stage without resolving its mechanism. | 97 | CI/CD pipeline implementation, release process definition. |
| 119 | What is the specific backward-compatible migration discipline required for Rolling Update safety — e.g., a mandatory two-phase migration pattern (additive change in one release, cleanup in a later release)? | [96_Deployment_Strategy.md](96_Deployment_Strategy.md) requires this discipline for Rolling Update readiness without specifying the concrete pattern engineers must follow. | 96 | Database migration process, schema change review standards. |
| 120 | What CI/CD platform executes the thirteen-stage pipeline (GitHub Actions, GitLab CI, Jenkins, or another)? | [97_CICD_Architecture.md](97_CICD_Architecture.md) explicitly defers this. | 97 | CI/CD implementation start. |
| 121 | What are the specific branch protection rules and required-approval counts per branch type? | [97_CICD_Architecture.md](97_CICD_Architecture.md) defers this alongside the CI/CD platform choice. | 97 | Version control workflow implementation. |
| 122 | What is the Code Review checklist's specific content? | [97_CICD_Architecture.md](97_CICD_Architecture.md) requires a Review Checklist element on every PR without defining what it verifies. | 97 | Code Review process implementation. |
| 123 | What is the auditable suppression mechanism for an exceptional, reviewed override of a Coding Standards or lint rule? | [99_Coding_Standards.md](99_Coding_Standards.md) requires such overrides to be "explicit, reviewed, and time-bound" without specifying the mechanism (e.g., an inline suppression comment linked to a tracked follow-up ticket). | 99 | Coding Standards enforcement tooling. |
| 124 | What linting/formatting tooling applies to SQL and Cypher, given the less standardized tooling ecosystem for these languages relative to Python/TypeScript? | [99_Coding_Standards.md](99_Coding_Standards.md) explicitly flags this as an open gap. | 99 | Code Quality tooling completeness for two of Cerebrum's four core languages. |
| 125 | What documentation authoring tool or platform hosts Module Documentation and Engineering Documentation (a static site generator, a wiki, inline-generated API docs, or a combination)? | [100_Documentation_Standards.md](100_Documentation_Standards.md) assumes Markdown consistency with this CES but does not resolve a hosting/publishing platform. | 100 | Documentation tooling setup. |
| 126 | What are the per-service Startup check completion criteria — which specific initialization steps (cache warming, initial datastore connection establishment, etc.) must complete before a service transitions from Startup to eligible-for-Readiness? | [101_Monitoring_Architecture.md](101_Monitoring_Architecture.md) introduces the Startup check without defining per-service completion criteria. | 101 | Health Check implementation, per service. |
| 127 | What are the specific backup frequency, retention period, and quantitative RPO/RTO targets for each datastore? | [102_Backup_Recovery.md](102_Backup_Recovery.md) establishes relative priority (PostgreSQL/MinIO tightest, Neo4j/Qdrant more tolerant) without numeric targets. | 102 | Backup infrastructure implementation, Disaster Recovery planning. |
| 128 | Does Cerebrum require single-tenant restoration capability (restoring one organization's data in isolation) as distinct from full-system restoration, given the shared-schema-with-Row-Level-Security multi-tenancy model? | [102_Backup_Recovery.md](102_Backup_Recovery.md) flags this as a materially more complex scenario worth evaluating once the multi-tenancy model was resolved (which [46_Multi_Tenancy.md](46_Multi_Tenancy.md) has since done). | 102, 46 | Disaster Recovery Procedures completeness, potential backup architecture extension. |

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Question 128 (single-tenant restoration) should be evaluated promptly given it directly follows from the multi-tenancy model decision already made in [46_Multi_Tenancy.md](46_Multi_Tenancy.md) and has significant Disaster Recovery architecture implications if the answer is yes.

## Constraints

- This list reflects ambiguities identifiable from the Part 9 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 95–103 rises to the level of a tracked open question here — routine, low-risk implementation latitude is intentionally not tracked.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the pattern established across Parts 1–8's Open Questions documents).
- With nine parts and 128 total accumulated questions across the full CES, a consolidated, theme-grouped cross-part Open Questions index — recommended since [74_Open_Questions.md](74_Open_Questions.md) and reiterated in every subsequent part's Open Questions document — should be treated as a required deliverable before architecture-implementation work begins, not an optional nicety.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific Part 9 document(s) it arose from.
- [ ] No question duplicates a question already recorded in any prior part's Open Questions document without adding DevOps/testing/engineering-standards-level specificity.
