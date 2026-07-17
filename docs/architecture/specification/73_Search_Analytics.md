# 73 — Search Analytics

## Purpose

This document defines the eight categories of search behavior Cerebrum tracks, elaborating FR-AL-001 (Search Analytics) from [20_Functional_Requirements.md](20_Functional_Requirements.md) with the specific metrics Part 6 requires, and reconciling them with the Evaluation Layer's metrics in [61_AI_Evaluation.md](61_AI_Evaluation.md) (Part 5).

## Scope

This document covers search-specific analytics tracking. It does not redefine the Analytics Domain's general architecture (see [35_Domain_Architecture.md](35_Domain_Architecture.md)) or AI Evaluation's conversational-response metrics (see [61_AI_Evaluation.md](61_AI_Evaluation.md)), which this document's metrics complement rather than duplicate.

## Definitions

- **Zero Result Query** — A query returning no results at all, distinct from a Failed Query (which returns an error rather than an empty result set).
- **Knowledge Gap** — A recurring query pattern with weak or absent supporting content, inferred from aggregated Zero Result and low-confidence-result query patterns.

## Tracked Metrics

Search Analytics SHALL track the following eight categories:

| Metric | Description | Primary Use |
|---|---|---|
| Most Frequent Queries | The highest-volume query patterns over a time window. | Identifies high-value content to prioritize for quality/freshness review. |
| Failed Queries | Queries that errored rather than completing, per [38_Observability.md](38_Observability.md)'s Search Error category. | Operational health monitoring, feeding [72_Search_Ranking.md](72_Search_Ranking.md) and connector-health correlation. |
| Zero Result Queries | See definition above. | Directly implements FR-AL-001's acceptance criteria ("zero-result queries are separately reportable to identify knowledge coverage gaps"). |
| Average Latency | Search Pipeline end-to-end timing ([71_Search_Pipeline.md](71_Search_Pipeline.md)), distinct from but comparable to the AI Request Lifecycle's latency tracking ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)). | Performance monitoring against the Search Response target ([39_Performance_Targets.md](39_Performance_Targets.md)). |
| CTR (Click-Through Rate) | Proportion of returned results a user actually opens/engages with. | Feeds [72_Search_Ranking.md](72_Search_Ranking.md)'s Popularity signal and ranking-quality assessment. |
| Popular Documents | The most frequently retrieved-and-engaged-with content. | Feeds Popularity ranking signal; also surfaces candidates for Knowledge Ownership review (FR-ED-004). |
| Popular Topics | Aggregated topic/keyword trends across queries (per FR-KP-007's extracted topics). | Informs organizational knowledge-priority understanding. |
| Knowledge Gaps | See definition above. | Directly supports the "reduce knowledge fragmentation" and "reduce search time" goals ([02_Project_Goals.md](02_Project_Goals.md)) by surfacing where Cerebrum's indexed knowledge does not yet meet demonstrated organizational demand. |

## Relationship to AI Evaluation (Part 5)

[61_AI_Evaluation.md](61_AI_Evaluation.md) tracks metrics for the AI Request Lifecycle's conversational responses (Grounding Accuracy, Hallucination Rate, Response Correctness, etc.). This document tracks metrics for the Search Pipeline's result-list interactions. Both feed the same underlying Analytics Domain infrastructure ([35_Domain_Architecture.md](35_Domain_Architecture.md)) and the same FR-AL-001/FR-AL-003 requirements from Part 2, but measure distinct user interactions — a query issued through the search interface produces Search Analytics; a query issued through the conversational interface produces AI Evaluation telemetry. A single underlying query (e.g., "who owns the payments service") could appear in both, if a user first searches, then asks the AI a follow-up — both interactions are tracked independently, and Knowledge Gap detection specifically SHOULD consider both sources together, since a gap visible only in Zero Result Queries but not in AI's Missing Information disclosures (or vice versa) is still a genuine gap.

## Responsibilities

- Every new Search Type added per [70_Enterprise_Search.md](70_Enterprise_Search.md) must emit the telemetry necessary to compute all eight tracked metrics for that type — an untracked search type undermines Knowledge Gap detection's completeness.
- Knowledge Gap detection should periodically cross-reference this document's Zero Result Queries with [61_AI_Evaluation.md](61_AI_Evaluation.md)'s Missing Information-flagged conversational responses, per the relationship stated above.

## Constraints

- This document does not specify the aggregation window, retention period, or dashboard presentation for these metrics — Deferred to Architecture/operations.
- CTR tracking must respect the same privacy considerations as Search History Audit access (Open Question 37 in [27_Open_Questions.md](27_Open_Questions.md)) — aggregate CTR reporting is a distinct, lower-sensitivity use case from per-user query-content audit access, and should be architected to avoid requiring the latter's elevated access control for the former's routine reporting.

## Future Considerations

- As Knowledge Gap detection matures, it could feed an automated recommendation to Administration ([62_AI_Governance.md](62_AI_Governance.md)-adjacent) suggesting new connector categories or content sources likely to close a detected gap, closing the loop between search behavior and knowledge coverage strategy.

## Acceptance Criteria

- [ ] All eight tracked metrics from the governing specification are defined with a primary use.
- [ ] The relationship between this document's Search Analytics and [61_AI_Evaluation.md](61_AI_Evaluation.md)'s AI Evaluation metrics is explicit, avoiding the appearance of two disconnected analytics systems.
- [ ] Knowledge Gap detection is defined as drawing on both search and conversational signals, not search data alone.
