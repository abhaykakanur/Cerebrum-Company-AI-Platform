# 49 — Open Questions (CES Phase 0, Part 4)

## Purpose

This document records data-architecture-specific ambiguities surfaced while writing [41_Data_Architecture.md](41_Data_Architecture.md) through [48_Data_Integrity.md](48_Data_Integrity.md). It extends, and does not replace, [11_Open_Questions.md](11_Open_Questions.md) (Part 1), [27_Open_Questions.md](27_Open_Questions.md) (Part 2), and [40_Open_Questions.md](40_Open_Questions.md) (Part 3). Per the governing specification's instruction, any data-architecture decision left uncertain is recorded here rather than resolved by assumption.

## Scope

This document covers ambiguities in data modeling, storage mechanics, and governance mechanisms. Numbering continues from [40_Open_Questions.md](40_Open_Questions.md) to maintain one unified backlog across all four CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 55 | Does OpenSearch (Part 3's chosen search technology) require its own formal treatment in this Data Architecture specification — tenant isolation model, entity ownership, and integrity rules — given the governing Part 4 specification named only PostgreSQL, Neo4j, Qdrant, Redis, and MinIO as the "canonical storage model"? | [41_Data_Architecture.md](41_Data_Architecture.md) through [48_Data_Integrity.md](48_Data_Integrity.md) reference OpenSearch's role (e.g., in [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Indexing stage) without giving it the same first-class ownership/isolation treatment as the five named datastores, since the governing specification for this phase did not list it among them. This is a specification gap, not a design decision, and should be closed explicitly. | 41, 42, 45, 46 | Enterprise Search Domain's data architecture completeness; potentially requires a 42-style addendum. |
| 56 | What is the concrete heuristic distinguishing a Major, Minor, and Patch version bump in the Versioning Model — is it human-declared at save time, automatically inferred from a content-diff magnitude, or a hybrid? | [44_Global_Entity_Model.md](44_Global_Entity_Model.md) defines the three-tier version fields but explicitly defers the bump-trigger heuristic. | 44 | Document Management and Knowledge Storage Domain implementation. |
| 57 | What is the specific tenant volume threshold (document count, vector count, query-per-second rate) that triggers provisioning a dedicated Neo4j database or Qdrant collection for a large tenant? | [46_Multi_Tenancy.md](46_Multi_Tenancy.md) establishes the escape-hatch pattern without a numeric trigger, deferring it to observed production load. | 46 | Capacity planning, Persistence Layer operational runbooks. |
| 58 | What are the legal-hold mechanics that override the Retention Sweep's hard-deletion eligibility check? | [47_Data_Governance.md](47_Data_Governance.md) requires the Retention Sweep to respect legal hold but does not define how a hold is placed, by whom, or how it is represented on an entity. Sharpens Open Question 5 in [11_Open_Questions.md](11_Open_Questions.md) to a concrete data-model requirement (a `LegalHold` entity or flag is implied but not specified). | 47 | Knowledge Storage Domain implementation, compliance/legal review. |
| 59 | Do Neo4j node labels follow Neo4j's own community convention (PascalCase) or Cerebrum's cross-store `snake_case` standard? | [47_Data_Governance.md](47_Data_Governance.md) explicitly flags this tension without resolving it. | 47 | Knowledge Graph Domain schema implementation. |
| 60 | Is the transactional outbox implemented via a polling worker (fixed interval) or a change-data-capture/log-tailing mechanism (e.g., listening to PostgreSQL's write-ahead log), and what is the outbox cleanup cadence for confirmed-propagated records? | [48_Data_Integrity.md](48_Data_Integrity.md) mandates the outbox pattern for cross-store write propagation but defers its specific implementation mechanism and housekeeping. | 48, 36 | Background Processing Layer implementation, cross-store propagation latency (relevant to the Freshness Signal mentioned in [41_Data_Architecture.md](41_Data_Architecture.md)). |
| 61 | Under what conditions, if any, does a tenant receive a dedicated Redis instance or resource quota to mitigate the noisy-neighbor risk flagged for shared-cache tenant isolation? | [46_Multi_Tenancy.md](46_Multi_Tenancy.md) identifies the gap (data isolation via key-prefixing does not address performance isolation) without proposing a trigger or mechanism. | 46 | Redis capacity planning. |
| 62 | Does PostgreSQL Row-Level Security's per-query performance overhead remain acceptable at the target scale (millions of documents, thousands of organizations), or does it require supplementing with table partitioning by `tenant_id`? | [46_Multi_Tenancy.md](46_Multi_Tenancy.md) commits to RLS as the enforcement mechanism without addressing its performance characteristics at the stated target scale from [39_Performance_Targets.md](39_Performance_Targets.md). | 46, 39 | PostgreSQL schema and partitioning strategy. |
| 63 | What is the specific Cypher query pattern (or post-query filtering logic) that guarantees a graph traversal cannot cross a relationship into a different tenant's node, given Neo4j's lack of native row-level security? | [46_Multi_Tenancy.md](46_Multi_Tenancy.md) states the requirement and notes the mechanism is "Deferred to Architecture for the specific Cypher pattern" without resolving it. | 46 | Knowledge Graph Domain repository adapter implementation, security testing (FR-SC-004). |
| 64 | What is the soft-delete grace period, per entity category, before Retention Sweep eligibility — is it a single global duration or does it vary (e.g., a User's grace period per FR-UM-006 vs. a Document's)? | [45_Data_Lifecycle.md](45_Data_Lifecycle.md) and [47_Data_Governance.md](47_Data_Governance.md) both reference "the applicable grace period" without enumerating category-specific values, which Part 2's FR-WS-005/FR-UM-006 also left as "Deferred to Architecture." | 45, 47 | Retention Sweep implementation. |
| 65 | Does the MinIO bucket-per-environment/region strategy in [46_Multi_Tenancy.md](46_Multi_Tenancy.md) need to vary by tenant based on data-residency requirements, and if so, how does object-key-prefix partitioning interact with region-specific bucket placement? | Data residency is named as a future consideration in [12_Future_Expansion.md](12_Future_Expansion.md) and Open Question 53 in [40_Open_Questions.md](40_Open_Questions.md), but its interaction with the specific prefix-based MinIO partitioning scheme decided in this Part is not addressed. | 46 | Object storage provisioning, data residency compliance. |
| 66 | Is the `MIGRATION` provenance-mechanism value in [47_Data_Governance.md](47_Data_Governance.md) sufficiently granular, or does it need sub-categorization (e.g., initial platform migration vs. a later bulk-import tool) for future audit/troubleshooting purposes? | Identified as a plausible gap while defining the provenance taxonomy; not yet justified by a concrete use case, so left open rather than speculatively expanded. | 47 | Provenance model completeness, low urgency pending an actual migration tool design. |

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Open Question 55 (OpenSearch's formal treatment) should be resolved first among this list, since several other Part 4 documents implicitly assume its answer is "yes, but out of this phase's explicit scope."

## Constraints

- This list reflects ambiguities identifiable from the Part 4 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 41–48 rises to the level of a tracked open question here — routine, low-risk implementation latitude is intentionally not tracked.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the pattern in [11_Open_Questions.md](11_Open_Questions.md), [27_Open_Questions.md](27_Open_Questions.md), and [40_Open_Questions.md](40_Open_Questions.md)) with a link to the governing ADR.
- Given how many Part 4 questions trace back to the still-unresolved multi-tenancy model questions from Part 1 (Open Question 3) and Part 3 (Open Questions 38, 41 — now resolved by [46_Multi_Tenancy.md](46_Multi_Tenancy.md)), a full backlog review across all four parts' Open Questions documents is recommended before architecture-implementation work begins, to confirm no contradictory resolutions exist between parts.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific Part 4 document(s) it arose from.
- [ ] No question duplicates a question already recorded in [11_Open_Questions.md](11_Open_Questions.md), [27_Open_Questions.md](27_Open_Questions.md), or [40_Open_Questions.md](40_Open_Questions.md) without adding data-architecture-level specificity.
