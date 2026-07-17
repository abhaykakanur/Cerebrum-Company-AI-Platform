# 53 — Query Planning

## Purpose

This document defines the Query Planning AI Subsystem Layer: what the Query Planner determines before retrieval begins, and how it selects a retriever configuration based on the Query Classification established in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md).

## Scope

This document covers query planning responsibilities and retriever-selection logic. It does not cover the retrieval strategies themselves (see [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) or context assembly after retrieval completes (see [54_Context_Assembly.md](54_Context_Assembly.md)).

## Definitions

- **Query Plan** — The Query Planning Layer's output: a structured specification of how a given query shall be retrieved, reasoned over, and formatted, consumed by every downstream pipeline stage.
- **Retrieval Budget** — The maximum volume of candidate content (measured in item count and/or token count) a retrieval pass is permitted to return before ranking and truncation.

## Query Planner Responsibilities

The Query Planner SHALL determine the following eleven elements of the Query Plan for every request, immediately after Query Classification (stage 5 of [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)):

| Element | Determines |
|---|---|
| Required data sources | Which Knowledge Source(s)/connector categories are in scope (e.g., a Code Query scopes to GitHub/GitLab-sourced content). |
| Required retrieval strategy | Which of the ten strategies in [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) apply, and in what combination. |
| Required graph traversal | Whether Graph Retrieval is needed, and to what depth (relevant for Relationship Query, Timeline Query classifications). |
| Required vector search | Whether Semantic Retrieval is needed (nearly always, except for narrowly-scoped Document Lookup by exact identifier). |
| Required metadata filters | Workspace scope, date range, source type, and other structural constraints derived from the query and its classification. |
| Required permission filters | Always required per Permission-aware Retrieval ([52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) — the Query Plan carries the requesting actor's identity for this purpose, never omits it. |
| Required reasoning strategy | Which of the reasoning types in [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md) applies (e.g., Comparison Query implies Comparative Reasoning). |
| Expected output format | Which response structure from [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md) fits the query (e.g., Timeline Query implies a Timeline View). |
| Required citations | Whether the query's classification implies a factual claim requiring citation (nearly always) or a purely conversational exchange that does not (rare, e.g., a clarifying question back to the user). |
| Maximum retrieval budget | The item-count ceiling for the retrieval pass(es), tuned per query classification (e.g., a Multi-document Query warrants a higher budget than a targeted Document Lookup). |
| Token budget | The context-size ceiling passed to Context Assembly ([54_Context_Assembly.md](54_Context_Assembly.md)), consistent with FR-RT-005. |

## Retriever Selection

Retriever Selection (stage 7 of [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) is the Query Planner's direct output applied: given the Query Plan's "required retrieval strategy" element, the specific retrieval strategies from [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) are instantiated and configured (e.g., graph traversal depth, metadata filter values) before Hybrid Retrieval executes.

### Illustrative Mapping: Classification to Strategy Selection

| Query Classification | Typical Strategy Selection |
|---|---|
| Entity Lookup | Graph Retrieval (primary) + Semantic Retrieval (secondary, for entity-mentioning content) |
| Relationship Query | Graph Retrieval (primary, multi-hop) |
| Timeline Query | Temporal Retrieval + Graph Retrieval (for entity/relationship timelines, FR-KG-007) |
| Multi-document Query | Multi-stage Retrieval, invoking Hybrid Retrieval per identified sub-topic |
| Comparison Query | Multi-stage Retrieval, one retrieval pass per compared item |
| Expert Discovery | Not a content-retrieval strategy at all — routed to the Expertise Discovery Domain's `findExperts` application service (FR-ED-001) directly, bypassing the standard Hybrid Retrieval path |

This table is illustrative, not exhaustive; the full mapping is Deferred to Architecture-time configuration, consistent with the Query Classification taxonomy's extensibility requirement in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) — a new classification requires a corresponding strategy-selection mapping entry, not a code change to the Query Planner itself.

## Responsibilities

- Every Query Plan element must be populated for every request — an empty or default-only Query Plan (e.g., always requesting all data sources) defeats the purpose of planning and degrades retrieval precision; this is a design defect, not an acceptable simplification.
- The Query Planner's strategy-selection mapping (classification → strategy) must be externally configurable, per the same extensibility rule as the Query Classification taxonomy.

## Constraints

- This document does not specify the algorithm by which the Query Planner itself is implemented (e.g., rule-based vs. a smaller classification model) — Deferred to Architecture.
- Retrieval and token budget default values are not specified here — Deferred to Architecture, configured via [62_AI_Governance.md](62_AI_Governance.md).

## Future Considerations

- As Evaluation Layer data ([61_AI_Evaluation.md](61_AI_Evaluation.md)) accumulates on retrieval precision/recall per classification, the classification-to-strategy mapping should be tuned empirically rather than left as an initial best-guess configuration indefinitely.

## Acceptance Criteria

- [ ] All eleven Query Planner responsibilities from the governing specification are defined.
- [ ] Retriever Selection is explicitly connected to Query Classification from [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md).
- [ ] The strategy-selection mapping is stated as externally configurable/extensible, not hard-coded.
