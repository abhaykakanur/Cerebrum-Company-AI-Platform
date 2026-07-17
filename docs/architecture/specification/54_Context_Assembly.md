# 54 — Context Assembly

## Purpose

This document defines the Context Construction AI Subsystem Layer: how retrieved evidence from multiple sources is collected, deduplicated, prioritized, and bounded into a single context for Reasoning. It elaborates FR-RT-002 (Context Assembly) and FR-RT-004/FR-RT-005 (Deduplication, Token Budgeting) from [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Scope

This document covers context assembly and token management. It does not cover retrieval itself (see [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) or how the assembled context is turned into a prompt (see [55_Prompt_Construction.md](55_Prompt_Construction.md), which consumes this layer's output).

## Definitions

- **Assembled Context** — The Retrieval Domain's structured, source-attributed output ([35_Domain_Architecture.md](35_Domain_Architecture.md)) that Prompt Construction consumes.
- **Context Budget** — The maximum token allocation available for the Assembled Context, distinct from the total model context window (which also reserves space for system instructions, conversation history, and the model's own output).

## Context Assembly Engine Responsibilities

The Context Assembly Engine SHALL perform the following eleven operations, in the order listed, on every request reaching stage 9 of [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md):

| # | Operation | Notes |
|---|---|---|
| 1 | Collect retrieved documents | Output of Hybrid Retrieval (stage 8). |
| 2 | Collect graph relationships | Where Graph Retrieval was part of the selected strategy. |
| 3 | Collect metadata | Structural metadata accompanying each retrieved item, needed for Citation ([57_Citation_Engine.md](57_Citation_Engine.md)). |
| 4 | Collect conversation history | From the Conversation Domain, per FR-CV-002's multi-turn context retention. |
| 5 | Collect memory | From the Memory Layer ([59_Memory_Architecture.md](59_Memory_Architecture.md)), only non-expired entries. |
| 6 | Collect citations | Pre-existing citations relevant to the query (e.g., from a referenced prior conversation turn), distinct from the new citations Citation Generation (stage 14) will produce. |
| 7 | Remove duplicates | Per FR-RT-004, using the same near-duplicate signal as FR-KI-005. |
| 8 | Prioritize authoritative sources | Using the Authority Signals from [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Hybrid Retrieval composition. |
| 9 | Maintain source ordering | A stable, deterministic order (by relevance rank, per FR-RT-003) — never reshuffled between identical requests, supporting deterministic Prompt Construction ([55_Prompt_Construction.md](55_Prompt_Construction.md)). |
| 10 | Optimize token utilization | See Token Management below. |
| 11 | Reject irrelevant context | Content falling below a minimum relevance threshold is excluded entirely rather than included at low priority, preventing dilution of the context with marginally relevant material. |

## Token Management

The AI SHALL support the following token management capabilities, directly implementing FR-RT-005:

| Capability | Description |
|---|---|
| Maximum Context Budget | A hard ceiling on Assembled Context size, set per Query Planning's token budget element ([53_Query_Planning.md](53_Query_Planning.md)) and never exceeded. |
| Chunk Prioritization | Ranking Chunks by relevance/authority (per [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s signals) to determine inclusion order when the candidate set exceeds budget. |
| Context Compression | Reducing token footprint of lower-priority included content (e.g., summarizing a long Chunk) while preserving its citation eligibility — Deferred to Architecture for the specific compression technique. |
| Redundancy Removal | A finer-grained pass than Duplicate Removal (operation 7 above) — trimming overlapping content between two non-duplicate but highly similar Chunks. |
| Citation Preservation | Per FR-RT-006: no compression, truncation, or redundancy-removal operation may strip a retained Chunk's source reference — content may be shortened, but its citability may never be lost. |
| Token Accounting | Tracking cumulative token usage as content is added, stopping before the Maximum Context Budget is exceeded rather than adding-then-checking. |
| Overflow Detection | Identifying, before Prompt Construction, that the ranked candidate set exceeds budget even after compression and redundancy removal. |
| Graceful Truncation | When overflow is detected, dropping the lowest-priority content first (per Chunk Prioritization), and recording that truncation occurred — consumed by Reasoning Transparency (FR-AR-008) so a user can learn that additional, lower-ranked evidence existed but was not included. |

## Responsibilities

- Every new content source added to Context Assembly (e.g., a new Memory category) must be explicitly added to the eleven-operation sequence above, in its correct position, not appended ad hoc after Reject Irrelevant Context.
- Token Management's Citation Preservation rule is non-negotiable — any compression or truncation technique proposed in later phases must be verified against this rule before adoption, per [48_Data_Integrity.md](48_Data_Integrity.md)'s Rule 1 pattern of verifying rather than assuming correctness.

## Constraints

- This document does not specify the exact relevance threshold for "Reject irrelevant context" or the specific compression algorithm — Deferred to Architecture.
- Context Budget default values are not specified here — Deferred to Architecture, configured via [62_AI_Governance.md](62_AI_Governance.md).

## Future Considerations

- As compression techniques mature, Context Compression's fidelity (how much semantic content survives compression) should become a tracked Evaluation Layer metric ([61_AI_Evaluation.md](61_AI_Evaluation.md)), since aggressive compression risks silently degrading grounding quality even while nominally preserving citations.

## Acceptance Criteria

- [ ] All eleven Context Assembly Engine operations from the governing specification are defined in their stated order.
- [ ] All eight Token Management capabilities from the governing specification are defined.
- [ ] Citation Preservation is stated as a non-negotiable constraint on every other Token Management capability, consistent with FR-RT-006.
