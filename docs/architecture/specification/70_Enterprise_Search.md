# 70 — Enterprise Search

## Purpose

This document defines the Enterprise Search Domain's architecture at the depth Part 6 requires: the eight qualities every search result must exhibit, and the sixteen supported search types. It elaborates FR-ES-001 through FR-ES-010 from [20_Functional_Requirements.md](20_Functional_Requirements.md) and reconciles this document set's search-type taxonomy with the Query Classification taxonomy already established in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) (Part 5).

## Scope

This document covers search principles and search-type taxonomy. It does not cover the search execution pipeline (see [71_Search_Pipeline.md](71_Search_Pipeline.md)) or ranking mechanics (see [72_Search_Ranking.md](72_Search_Ranking.md)).

## Definitions

- **Enterprise Search** — The human-facing, result-list-returning search capability, architecturally distinct from the Retrieval Domain's AI-reasoning-facing context assembly (per [31_Component_Architecture.md](31_Component_Architecture.md)'s established separation), though both draw on the same underlying indexes and retrieval mechanics.
- **Search Type** — A query-shape-specific search behavior, most of which correspond directly to a Query Classification from [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) applied at the search-result-list layer rather than the conversational-answer layer.

## Search Principles

Enterprise Search SHALL be:

| Principle | Meaning | Established In |
|---|---|---|
| Permission Aware | No result reveals content or existence beyond the requesting user's authorization. | FR-ES-010, FR-AUTZ-003 |
| Explainable | A result's inclusion and ranking can be explained on request. | FR-ES-009 |
| Grounded | Results are real, indexed enterprise content — never a generated or inferred item presented as if it were retrieved. | AI Design Philosophy ([50_AI_Architecture.md](50_AI_Architecture.md)) applied to search |
| Hybrid | Combining keyword and semantic signals by default. | FR-ES-003 |
| Fast | Meeting the Search Response performance target. | [39_Performance_Targets.md](39_Performance_Targets.md) |
| Consistent | The same query and permission context yields materially consistent results across repeated executions. | Mirrors [55_Prompt_Construction.md](55_Prompt_Construction.md)'s determinism principle, applied to search ranking |
| Extensible | New search types and ranking signals can be added without architectural redesign. | Open/Closed, [34_Architecture_Principles.md](34_Architecture_Principles.md) |
| Source Agnostic | Search behaves consistently regardless of which connector category a result originates from. | Directly supports "reduce knowledge fragmentation," [02_Project_Goals.md](02_Project_Goals.md) |

## Supported Search Types

The following sixteen search types are supported. Most correspond directly to a Query Classification already defined in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md); this table makes that correspondence explicit rather than introducing a parallel, disconnected taxonomy.

| Search Type | Description | Corresponding Query Classification (Part 5) |
|---|---|---|
| Keyword Search | Exact/stemmed term matching. | Informational Query, Search Query |
| Semantic Search | Embedding-similarity matching. | Informational Query, Search Query |
| Hybrid Search | Combined keyword + semantic. | Search Query (default mode) |
| Graph Search | Knowledge Graph traversal-based. | Relationship Query |
| Metadata Search | Structural-field filtering. | Document Lookup |
| Entity Search | Search scoped to a specific Knowledge Entity. | Entity Lookup |
| Relationship Search | Search for content connecting two or more entities. | Relationship Query |
| Decision Search | Search scoped to Decision Intelligence records. | Decision Query |
| Meeting Search | Search scoped to Meeting Intelligence records. | Meeting Query |
| Architecture Search | Search scoped to Architecture Memory. | Architecture Query |
| Conversation Search | Search over a user's own Conversation History. | Conversation Follow-up (retrospective variant — searching past conversations rather than continuing one) |
| Timeline Search | Chronologically ordered search results. | Timeline Query |
| Expert Search | Search for people rather than content. | Expert Discovery — routed to the Expertise Discovery Domain's `findExperts`, not standard content retrieval, per [53_Query_Planning.md](53_Query_Planning.md)'s illustrative mapping |
| Document Search | Search scoped to Document Management. | Document Lookup |
| Policy Search | Search scoped to Policy content, current-version-preferring. | Policy Query |
| Project Search | Search scoped to Project Memory. | Project Query |

**Reconciliation note:** Part 5's Query Classification taxonomy governs the AI Request Lifecycle (conversational, answer-synthesizing); this document's Search Type taxonomy governs Enterprise Search (result-list-returning). Both taxonomies describe the same underlying query-shape distinctions because both consume the same Query Understanding and Query Planning capability ([50_AI_Architecture.md](50_AI_Architecture.md), [53_Query_Planning.md](53_Query_Planning.md)) — a query classified as a "Decision Query" by Query Understanding drives "Decision Search" behavior when the user is browsing Enterprise Search results, and "Decision Reasoning" ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)) when the user is in a conversational exchange. This is one taxonomy with two consuming surfaces, not two independent taxonomies that happen to overlap.

**Extensibility:** New search types SHALL be addable following the same registry-based extensibility pattern already established for Query Classification in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) — a new search type and a new query classification should typically be added together, given their direct correspondence.

## Responsibilities

- Every new search type proposed in a later phase must be reconciled against the Query Classification taxonomy in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) before being added — an unreconciled addition risks the two taxonomies silently diverging.
- The eight Search Principles are binding on every search type — a search type that cannot be made Permission Aware, for instance, is not a valid addition to this catalog.

## Constraints

- This document does not specify the OpenSearch/Qdrant/Neo4j query implementation for any search type — Deferred to Architecture, per [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s retrieval-strategy architecture, which these search types consume.
- Consistency (a search principle) is bounded by the same underlying-index-freshness caveat already established in [41_Data_Architecture.md](41_Data_Architecture.md)'s eventual-consistency resolution — "consistent" means deterministic ranking for a given index state, not that the index itself is always instantaneously up to date.

## Future Considerations

- As new Query Classifications are added per [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)'s extensibility mechanism, a corresponding Search Type should be evaluated for addition here, maintaining the one-taxonomy-two-surfaces relationship.

## Acceptance Criteria

- [ ] All eight Search Principles from the governing specification are defined.
- [ ] All sixteen Search Types from the governing specification are defined and reconciled with Part 5's Query Classification taxonomy, not left as a disconnected parallel list.
- [ ] The distinction between Enterprise Search (this document) and the Retrieval Domain (Part 5) is restated clearly enough to prevent confusion between the two.
