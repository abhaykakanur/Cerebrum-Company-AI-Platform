# 51 — AI Request Lifecycle

## Purpose

This document defines the complete pipeline every AI request follows, from user query to response delivery, mapping each stage to its owning AI Subsystem Layer ([50_AI_Architecture.md](50_AI_Architecture.md)). It also defines the Query Classification taxonomy that gates the pipeline's early stages, the failure-handling protocol for each stage, and stage-level performance targets.

## Scope

This document covers pipeline sequencing, classification taxonomy, failure handling, and performance targets. It does not cover any individual stage's internal design in depth — see documents 52–63 for that detail, cross-referenced per stage below.

## Definitions

- **Pipeline Stage** — One discrete, ordered step in the AI Request Lifecycle, each with a defined entry condition, owning layer, and exit condition.
- **Query Classification** — The taxonomy category assigned to an incoming query before retrieval, determining which retrieval and reasoning strategies apply.

## The AI Request Lifecycle

Every AI request SHALL progress through the following eighteen stages in order, except where explicitly noted as parallelizable. This elaborates the Conversation Domain's `submitQuery` flow ([35_Domain_Architecture.md](35_Domain_Architecture.md)) with AI-subsystem-specific detail.

| # | Stage | Owning Layer | Requirement Traceability |
|---|---|---|---|
| 1 | User Query | Conversation Domain (not an AI Subsystem Layer — the entry point) | FR-CV-001 |
| 2 | Authentication | Authentication Layer | FR-AUTH-007 |
| 3 | Authorization | Authorization Layer | FR-AUTZ-003 |
| 4 | Intent Analysis | Query Understanding | New in Part 5; determines the user's underlying goal independent of surface phrasing. |
| 5 | Query Classification | Query Understanding | See Query Classification Taxonomy below. |
| 6 | Query Planning | Query Planning | FR-AR-004 (decomposition is one planning outcome); see [53_Query_Planning.md](53_Query_Planning.md). |
| 7 | Retriever Selection | Query Planning | Determines which of the ten retrieval strategies in [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) apply. |
| 8 | Hybrid Retrieval | Retrieval | FR-RT-001; see [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md). |
| 9 | Context Assembly | Context Construction | FR-RT-002; see [54_Context_Assembly.md](54_Context_Assembly.md). |
| 10 | Context Optimization | Context Construction | FR-RT-004, FR-RT-005 (deduplication, token budgeting); see [54_Context_Assembly.md](54_Context_Assembly.md). |
| 11 | Prompt Construction | Reasoning | See [55_Prompt_Construction.md](55_Prompt_Construction.md). |
| 12 | LLM Invocation | Reasoning | FR-AR-001; see [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md), [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md). |
| 13 | Evidence Validation | Validation | FR-AR-005; see [58_Confidence_Engine.md](58_Confidence_Engine.md). |
| 14 | Citation Generation | Citation | FR-CT-001; see [57_Citation_Engine.md](57_Citation_Engine.md). |
| 15 | Confidence Scoring | Confidence | FR-CF-001; see [58_Confidence_Engine.md](58_Confidence_Engine.md). |
| 16 | Response Formatting | Response Generation | FR-AR-007; see [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md). |
| 17 | Audit Logging | Audit Domain (not an AI Subsystem Layer) | FR-AU-001, satisfying the "AI Response" auditable action in [47_Data_Governance.md](47_Data_Governance.md). |
| 18 | Response Delivery | Conversation Domain | FR-CV-001. |

Stages 4–5 (Intent Analysis, Query Classification) may execute concurrently where architecturally beneficial, since both operate on the same input (the raw query) without depending on each other's output; stages 14–15 (Citation Generation, Confidence Scoring) likewise may execute concurrently, since Confidence Scoring depends on Evidence Validation's outcome (stage 13), not Citation Generation's. All other stages are strictly sequential, each depending on its predecessor's output.

## Query Classification Taxonomy

Every incoming query SHALL be classified into exactly one of the following categories before retrieval (stage 5), directly determining Query Planning's retrieval-strategy selection (stage 6–7):

| Classification | Description | Primary Retrieval Strategy Implication |
|---|---|---|
| Informational Query | General knowledge lookup. | Hybrid retrieval, broad scope. |
| Document Lookup | User seeks a specific, identifiable document. | Metadata/keyword-weighted retrieval. |
| Entity Lookup | User seeks information about a specific person, system, or project. | Graph retrieval (FR-KG-006). |
| Relationship Query | User asks how two or more entities relate. | Graph traversal-weighted retrieval. |
| Meeting Query | User asks about meeting content. | Meeting Intelligence-scoped retrieval. |
| Decision Query | User asks about a decision. | Decision Intelligence-scoped retrieval. |
| Policy Query | User asks about organizational policy. | Policy-scoped retrieval, current-version-preferring (FR-EM-008). |
| Architecture Query | User asks about technical architecture. | Architecture Memory-scoped retrieval (FR-EM-003). |
| Code Query | User asks about source code. | Code-connector-scoped retrieval. |
| Expert Discovery | User seeks a person with specific expertise. | Expertise Discovery Domain query (FR-ED-001), not content retrieval. |
| Timeline Query | User asks how something evolved over time. | Temporal retrieval (FR-KG-007). |
| Project Query | User asks about a project's status or history. | Project Memory-scoped retrieval (FR-EM-004). |
| Search Query | User issues a broad, exploratory search. | Full hybrid retrieval, human-facing ranking (Enterprise Search, not Retrieval Domain). |
| Analytical Query | User asks for synthesis or analysis across sources. | Multi-stage retrieval, cross-document reasoning (FR-AR-003). |
| Comparison Query | User asks to compare two or more things. | Multi-stage retrieval targeting each compared item. |
| Multi-document Query | Query inherently spans several distinct sources. | Multi-stage retrieval; see [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md). |
| Summarization | User asks for a summary of known content. | Targeted retrieval of the specific content to summarize. |
| Conversation Follow-up | Query depends on prior conversation turns. | Memory-augmented retrieval (FR-CV-002). |
| Unknown Query | Classification could not be determined with sufficient confidence. | Falls back to Informational Query's broad hybrid retrieval, flagged as low-confidence classification for Evaluation Layer tracking. |

**Extensibility:** New classifications SHALL be addable without architectural redesign — the classification taxonomy is a configurable enumeration consumed by Query Planning's strategy-selection logic (a lookup, not hard-coded branching), consistent with Plugin-Ready/Open-Closed principles from [34_Architecture_Principles.md](34_Architecture_Principles.md). The `Unknown Query` category exists precisely so an unrecognized query never blocks the pipeline while awaiting a new classification's addition.

## Failure Handling

The AI subsystem SHALL gracefully handle the following failure scenarios, mapped to the pipeline stage(s) where they arise. In every scenario, the system SHALL: log the failure (per [38_Observability.md](38_Observability.md)'s AI Error category), preserve diagnostics (for the Evaluation Layer, [61_AI_Evaluation.md](61_AI_Evaluation.md)), avoid hallucination (never substitute a fabricated answer for the failed step's output), return meaningful user feedback, and suggest a corrective action where one exists.

| Failure Scenario | Arising At Stage(s) | Handling |
|---|---|---|
| No Results Found | Hybrid Retrieval (8) | Proceed to Reasoning with empty context; Reasoning Layer returns an explicit "unknown" per FR-AR-006, not an empty or generic response. |
| Retriever Failure | Hybrid Retrieval (8) | Degrade to available retrieval strategies (e.g., keyword-only if semantic retrieval's Qdrant dependency fails), flagged as degraded-mode per [38_Observability.md](38_Observability.md)'s Search Error handling. |
| Embedding Failure | Hybrid Retrieval (8) | Fall back to non-semantic retrieval strategies for this request; the underlying embedding provider issue is escalated per [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)'s provider health handling. |
| Provider Timeout | LLM Invocation (12) | Retry per the fallback policy in [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md); if exhausted, return an explicit service-degradation response, never a partial or fabricated answer. |
| Provider Failure | LLM Invocation (12) | Same as Provider Timeout. |
| Context Overflow | Context Optimization (10) | Graceful truncation per [54_Context_Assembly.md](54_Context_Assembly.md)'s Token Management, never silent content loss without the truncation being recorded for Reasoning Transparency (FR-AR-008). |
| Permission Failure | Authorization (3), or discovered later during Retrieval (8) | Immediately fail the request with a Security Error per [38_Observability.md](38_Observability.md) — never retried, never degraded. |
| Graph Failure | Hybrid Retrieval (8) | Degrade to non-graph retrieval strategies for this request; Knowledge Graph Domain's own health status (FR-MN-001) is separately monitored. |
| Search Failure | Hybrid Retrieval (8) | Degrade to available strategies, consistent with [38_Observability.md](38_Observability.md)'s Search Error graceful-degradation rule. |
| Rate Limits | LLM Invocation (12), Hybrid Retrieval (8) | Queue and retry with backoff per [36_Background_Processing.md](36_Background_Processing.md)'s retry policy pattern, applied synchronously within the request's latency budget up to a defined limit before failing visibly. |
| Partial Data Availability | Any retrieval stage | Proceed with available data; the resulting lower Evidence Coverage is reflected in Confidence Scoring (stage 15), never silently treated as complete. |

## Performance Targets

The following stage-level targets refine, at finer grain, the end-to-end targets in [39_Performance_Targets.md](39_Performance_Targets.md) — Intent Classification and Hybrid Retrieval's targets are sub-budgets within that document's Chat Response First Token target, not additive to it.

| Stage | Target | Relationship to [39_Performance_Targets.md](39_Performance_Targets.md) |
|---|---|---|
| Intent Classification (stage 4) | < 100 ms | Sub-budget within Chat Response First Token. |
| Hybrid Retrieval (stage 8) | < 1000 ms | Directly corresponds to the Knowledge Retrieval target (< 1 second). |
| Prompt Construction (stage 11) | < 300 ms | Sub-budget within Chat Response First Token. |
| Time to First Token (through stage 12's first streamed token) | < 3000 ms | Directly corresponds to the Chat Response First Token target. |
| Average AI Response (full pipeline, stages 1–18) | < 8000 ms | A new, more complete end-to-end target than [39_Performance_Targets.md](39_Performance_Targets.md) specified, covering post-generation stages (citation, confidence, formatting) that target did not separately budget. |
| Citation Generation (stage 14) | < 500 ms | New; executes concurrently with Confidence Scoring per the Lifecycle table above. |
| Confidence Calculation (stage 15) | < 300 ms | New; executes concurrently with Citation Generation. |

## Responsibilities

- Every new pipeline capability introduced in a later phase must be placed into one of the eighteen stages above, or trigger an ADR proposing a new stage, per [09_Governance.md](09_Governance.md).
- The Query Classification taxonomy's extensibility mechanism (configurable enumeration, not hard-coded branching) is binding — a later implementation adding a classification via a new `if` branch rather than a registry entry is a review-blocking finding.

## Constraints

- This document does not specify the intent-classification or query-classification model/technique — Deferred to Architecture.
- Performance targets here are Version 1.0 architectural design goals, per the same caveat stated in [39_Performance_Targets.md](39_Performance_Targets.md), not contractual SLAs.

## Future Considerations

- As new query classification categories prove necessary in production, the taxonomy should grow via the registry mechanism described above, with each addition traced to an observed gap (e.g., a recurring pattern previously falling into `Unknown Query`).

## Acceptance Criteria

- [ ] All eighteen pipeline stages from the governing specification are represented with an owning layer and requirement traceability.
- [ ] All nineteen query classifications from the governing specification are defined with a retrieval-strategy implication, and extensibility is explicitly addressed.
- [ ] All eleven failure scenarios from the governing specification are addressed with a concrete handling rule, not a generic "handle gracefully" statement.
- [ ] All seven performance targets from the governing specification are stated and reconciled with [39_Performance_Targets.md](39_Performance_Targets.md).
