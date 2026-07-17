# 74 — Open Questions (CES Phase 0, Part 6)

## Purpose

This document records connector- and search-architecture-specific ambiguities surfaced while writing [65_Connector_Architecture.md](65_Connector_Architecture.md) through [73_Search_Analytics.md](73_Search_Analytics.md). It extends, and does not replace, [11_Open_Questions.md](11_Open_Questions.md) (Part 1), [27_Open_Questions.md](27_Open_Questions.md) (Part 2), [40_Open_Questions.md](40_Open_Questions.md) (Part 3), [49_Open_Questions.md](49_Open_Questions.md) (Part 4), and [64_Open_Questions.md](64_Open_Questions.md) (Part 5). Ambiguity is recorded here rather than resolved by assumption.

## Scope

This document covers ambiguities in connector and search design left unresolved by documents 65–73. Numbering continues from [64_Open_Questions.md](64_Open_Questions.md) to maintain one unified backlog across all six CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 81 | What is the specific mechanism for mapping a source-system user identity to a Cerebrum User account during Permission Synchronization, particularly where no exact email match exists? | [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Users element requires this mapping without specifying a matching algorithm or a fallback for unmatched identities. | 68 | Permission Synchronization Engine implementation. |
| 82 | What is the required process for documenting a connector's permission-API limitations (per-connector reduced-granularity permission sync), and how is this limitation surfaced to administrators configuring that connector? | [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md) requires documentation of such limitations but does not specify the format or administrator-facing disclosure mechanism. | 68 | Connector Plugin implementation standards, Administration Layer UX. |
| 83 | What are the specific Circuit Breaker thresholds (consecutive failure count, cool-down duration) per connector category? | [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md) requires per-category tuning without specifying values, extending the general Background Processing circuit-breaker question (Open Question 51 in [40_Open_Questions.md](40_Open_Questions.md)) with connector-category-specific granularity. | 68 | Retry Engine implementation. |
| 84 | What semantic versioning scheme governs Connector Version, and what constitutes a breaking vs. non-breaking change for a connector plugin? | [66_Connector_SDK.md](66_Connector_SDK.md) requires Connector Versioning to exist without defining the scheme or breaking-change criteria. | 66 | Connector SDK implementation, plugin upgrade tooling. |
| 85 | What is the deprecation window for an SDK contract breaking change, analogous to the external API deprecation window question (Open Question 36 in [40_Open_Questions.md](40_Open_Questions.md)) but for the internal connector-plugin ecosystem? | [66_Connector_SDK.md](66_Connector_SDK.md) requires backward-compatibility review for SDK changes without specifying a deprecation timeline. | 66 | Connector SDK governance process. |
| 86 | How lightweight is the Metadata Discovery lifecycle stage intended to be — does it enumerate every item's basic metadata, or only aggregate counts/structure sufficient for sync planning? | [67_Connector_Lifecycle.md](67_Connector_Lifecycle.md) introduces this stage without fully specifying its scope boundary relative to the full per-item extraction at Document Fetch. | 67 | Metadata Extraction Engine implementation, sync-time estimation accuracy. |
| 87 | For Database and Object Storage connector categories (PostgreSQL, MySQL, S3, etc.), what specific content boundary defines what gets extracted as organizational knowledge — every table/row, a configured subset of schemas, or only unstructured content (e.g., text/BLOB columns) rather than transactional data? | [65_Connector_Architecture.md](65_Connector_Architecture.md)'s expanded catalog adds these categories without resolving how Cerebrum's document-oriented ingestion pipeline ([45_Data_Lifecycle.md](45_Data_Lifecycle.md)) applies to inherently structured, high-volume database content, distinct from the non-goal boundary already established (Cerebrum is not a database client application, per [07_Non_Goals.md](07_Non_Goals.md)). | 65 | Database connector plugin design, Non-Goals boundary clarification. |
| 88 | How is Popularity ([72_Search_Ranking.md](72_Search_Ranking.md)) specifically measured — raw view count, click-through rate, citation frequency in AI responses, or a composite? | The document requires the signal without specifying its computation, deferring to Search Analytics data that does not yet exist to inform the choice. | 72, 73 | Search ranking implementation. |
| 89 | What are the default relative weights for the ten Search Ranking signals and the (separately configured) ten Hybrid Retrieval signals? | [72_Search_Ranking.md](72_Search_Ranking.md) and [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) both require configurable weighting without proposing defaults. | 72, 52 | Enterprise Search and Retrieval implementation, [62_AI_Governance.md](62_AI_Governance.md) default configuration. |
| 90 | What algorithm extracts the "Relevant Snippet" field for a search result, and how does it differ from AI-generated summarization? | [71_Search_Pipeline.md](71_Search_Pipeline.md)'s Search Result Requirements names this field without specifying extraction technique. | 71 | Search result formatting implementation. |
| 91 | How is Click-Through Rate tracking architected to support aggregate ranking-signal and analytics use (low sensitivity, routine access) without requiring the elevated access-control justification workflow that Search History Audit access carries (Open Question 37 in [27_Open_Questions.md](27_Open_Questions.md))? | [73_Search_Analytics.md](73_Search_Analytics.md) flags this tension without resolving the specific architectural separation between aggregate and per-user query data. | 73 | Analytics Domain data model, privacy architecture. |
| 92 | What threshold or pattern-detection method determines that a set of Zero Result / low-confidence queries constitutes a genuine "Knowledge Gap" worth surfacing, as opposed to isolated, non-recurring queries? | [73_Search_Analytics.md](73_Search_Analytics.md) requires Knowledge Gap detection without defining the recurrence threshold or clustering method. | 73 | Knowledge Gap detection implementation, Analytics Domain reporting. |

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Question 87 (database/object-storage connector content boundary) should be prioritized early, since it has a direct bearing on whether the Non-Goals boundary in [07_Non_Goals.md](07_Non_Goals.md) needs a governance-reviewed clarification before those connector categories are built.

## Constraints

- This list reflects ambiguities identifiable from the Part 6 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 65–73 rises to the level of a tracked open question here — routine, low-risk implementation latitude is intentionally not tracked.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the pattern in Parts 1–5's Open Questions documents) with a link to the governing ADR.
- Given six parts' worth of accumulated Open Questions documents, a consolidated cross-part Open Questions index (grouped by theme — tenancy, AI safety, connector scope, etc. — rather than strictly by part) is recommended before architecture-implementation work begins in earnest, to make related questions across parts easier to resolve together.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific Part 6 document(s) it arose from.
- [ ] No question duplicates a question already recorded in [11_Open_Questions.md](11_Open_Questions.md), [27_Open_Questions.md](27_Open_Questions.md), [40_Open_Questions.md](40_Open_Questions.md), [49_Open_Questions.md](49_Open_Questions.md), or [64_Open_Questions.md](64_Open_Questions.md) without adding connector/search-architecture-level specificity.
