# 52 — Retrieval Architecture

## Purpose

This document defines the Retrieval AI Subsystem Layer's architecture: the ten supported retrieval strategies, how Hybrid Retrieval composes multiple signals into one ranked candidate set, and the query rewriting techniques applied before retrieval executes. It elaborates FR-RT-001 (Hybrid Retrieval) from [20_Functional_Requirements.md](20_Functional_Requirements.md) and the Retrieval Domain architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Scope

This document covers retrieval strategy and query rewriting. It does not cover what happens to retrieved results afterward (see [54_Context_Assembly.md](54_Context_Assembly.md)) or how a query is planned before retrieval begins (see [53_Query_Planning.md](53_Query_Planning.md), which selects which strategies from this document apply to a given query).

## Definitions

- **Retrieval Strategy** — One of ten distinct methods for locating relevant content, each suited to a different query shape or classification.
- **Query Rewriting** — Transforming a user's original query into a form more effective for retrieval, without discarding the original.

## Supported Retrieval Strategies

The retrieval engine SHALL support the following ten strategies, selected and combined per Query Planning's strategy selection ([53_Query_Planning.md](53_Query_Planning.md)):

| Strategy | Description | Primary Datastore |
|---|---|---|
| Keyword Retrieval | Exact and stemmed term matching. | OpenSearch (FR-ES-001) |
| Semantic Retrieval | Embedding-similarity matching. | Qdrant (FR-ES-002) |
| Hybrid Retrieval | Combines keyword and semantic signals — see below. | OpenSearch + Qdrant (FR-ES-003) |
| Graph Retrieval | Traversal from a known entity through the Knowledge Graph. | Neo4j (FR-KG-006, FR-ES-006) |
| Metadata Retrieval | Filtering by structural metadata (source, type, author, date). | PostgreSQL/OpenSearch (FR-ES-004) |
| Temporal Retrieval | Filtering/ranking by time range or chronological ordering. | PostgreSQL/Neo4j (FR-KG-007) |
| Relationship Retrieval | Locating content connected to a specific entity via a specific relationship type. | Neo4j |
| Permission-aware Retrieval | Filtering all of the above to only content the requesting user is authorized for. | Cross-cutting — applied by every strategy, never optional (FR-AUTZ-003) |
| Incremental Retrieval | Fetching additional results beyond an initial page/budget when a follow-up query needs more depth. | Cross-cutting — a retrieval-budget extension, not a distinct data source |
| Multi-stage Retrieval | Sequential retrieval passes where a later pass's query depends on an earlier pass's results (e.g., retrieve an entity, then retrieve content related to it). | Cross-cutting — orchestrates the other strategies across multiple passes |

Permission-aware Retrieval is not a peer strategy alongside the other nine — it is a mandatory constraint applied to every one of them, directly implementing FR-ES-010's and FR-AUTZ-003's requirement that no retrieval path bypasses permission enforcement.

## Hybrid Retrieval Composition

Hybrid Retrieval SHALL combine the following ten signals into a single ranked candidate set:

| Signal | Source | Purpose |
|---|---|---|
| BM25 | OpenSearch keyword scoring | Lexical relevance. |
| Vector Search | Qdrant cosine/dot-product similarity | Semantic relevance. |
| Knowledge Graph Traversal | Neo4j | Relational relevance (content connected to query-relevant entities). |
| Metadata Filtering | PostgreSQL/OpenSearch | Excludes/boosts by structural criteria (source type, workspace scope). |
| Recency Signals | Base Entity Envelope timestamps ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)) | Favors fresher content where the query classification implies recency matters (e.g., Timeline Query). |
| Authority Signals | Expertise Discovery Domain's ownership attribution (FR-ED-004), source-system trust tier | Favors content from authoritative sources/owners. |
| Permission Constraints | Authorization Layer | Excludes unauthorized content — never a ranking factor, always a hard filter. |
| Source Reliability | Knowledge Quality Validation outcome (FR-KP-010) | De-weights or excludes flagged low-quality content. |
| Result Ranking | Composite scoring function | Combines the above into one ordered list. |
| Duplicate Removal | Duplicate Detection outcome (FR-KI-005) | Prevents near-duplicate content from crowding out diverse results. |

**Weighting configurability:** The relative weighting between these signals SHALL be configurable per the AI Administration Layer ([62_AI_Governance.md](62_AI_Governance.md)), consistent with FR-ES-003's "relative weighting between signals is configurable" acceptance criterion — default weights are Deferred to Architecture.

**Distinction from Enterprise Search:** This Hybrid Retrieval composition serves the Retrieval AI Subsystem Layer (feeding Reasoning), tuned for evidentiary completeness. The Enterprise Search Domain's own hybrid search (FR-ES-003, human-facing) uses the same underlying signals but tunes for human-scannable ranking, per the distinction already established in [31_Component_Architecture.md](31_Component_Architecture.md) between the Retrieval Layer and Enterprise Search.

## Query Rewriting

Before retrieval executes, the AI SHALL apply query rewriting to improve retrieval effectiveness, using the following techniques as applicable to the classified query:

| Technique | Purpose |
|---|---|
| Synonym Expansion | Broadens matching for common synonyms (e.g., "onboarding" / "orientation"). |
| Abbreviation Expansion | Expands known abbreviations (e.g., "SSO" → "Single Sign-On"). |
| Technology Aliases | Resolves alternate names for the same technology (e.g., "Postgres" / "PostgreSQL"). |
| Department Aliases | Resolves organization-specific department naming variance. |
| Company Terminology | Resolves internal jargon or product code names to their canonical referent. |
| Context Completion | Fills in implied context from the Memory Layer (e.g., "the project" resolved from conversation context). |
| Entity Resolution | Matches a mentioned name to a specific Knowledge Graph entity, disambiguating where multiple candidates exist. |
| Spell Correction | Corrects likely typos before matching. |
| Query Simplification | Reduces a verbose query to its retrieval-relevant core. |
| Query Decomposition | Splits a compound query into sub-queries, per FR-AR-004, coordinated with Query Planning ([53_Query_Planning.md](53_Query_Planning.md)). |

**Binding rule:** The original user query SHALL always be preserved alongside any rewritten form — used for audit logging (stage 17 of [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)), Reasoning Transparency (FR-AR-008), and as a fallback if a rewrite degrades retrieval quality for a given query shape.

## Responsibilities

- Every new retrieval strategy proposed in a later phase must be added to the Supported Retrieval Strategies table with a stated datastore and interaction with Permission-aware Retrieval before implementation.
- Query rewriting techniques operate as a pipeline of independent, individually testable transformations (per Composition over Inheritance in [34_Architecture_Principles.md](34_Architecture_Principles.md)) — not as a single monolithic rewriting function.

## Constraints

- This document does not specify the specific algorithm or model used for any rewriting technique (e.g., which NER model performs Entity Resolution) — Deferred to Architecture.
- Default Hybrid Retrieval signal weights are not specified here — Deferred to Architecture, configured via [62_AI_Governance.md](62_AI_Governance.md).

## Future Considerations

- As new connector categories are added (per [12_Future_Expansion.md](12_Future_Expansion.md)), their content may warrant source-specific retrieval tuning (e.g., code-aware retrieval for GitHub content) as an extension of Metadata Retrieval rather than a new top-level strategy.

## Acceptance Criteria

- [ ] All ten retrieval strategies from the governing specification are defined with a clear description and datastore.
- [ ] All ten Hybrid Retrieval signals from the governing specification are defined, with weighting explicitly stated as configurable.
- [ ] All ten query rewriting techniques from the governing specification are defined, with the original-query-preservation rule stated as binding.
