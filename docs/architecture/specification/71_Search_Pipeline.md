# 71 — Search Pipeline

## Purpose

This document defines the Enterprise Search Domain's own request pipeline — structurally parallel to, but distinct from, the AI Request Lifecycle in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) — along with Query Rewriting as applied to search, Autocomplete, Filtering, and the required fields on every search result.

## Scope

This document covers the search-specific pipeline and its supporting capabilities (rewriting, autocomplete, filtering, result structure). It does not cover the AI Request Lifecycle's conversational pipeline (see [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) or ranking signal detail (see [72_Search_Ranking.md](72_Search_Ranking.md), which this pipeline's Ranking stage invokes).

## Definitions

- **Search Pipeline** — The eleven-stage sequence a human-facing search query follows, ending in a ranked result list rather than a synthesized natural-language answer.

## The Search Pipeline

Every Enterprise Search query SHALL follow the eleven stages below:

| # | Stage | Notes |
|---|---|---|
| 1 | User Query | Entry point, per FR-ES-001's baseline. |
| 2 | Intent Classification | Reuses Query Understanding's Intent Analysis capability ([50_AI_Architecture.md](50_AI_Architecture.md)), determining the Search Type per [70_Enterprise_Search.md](70_Enterprise_Search.md). |
| 3 | Permission Validation | Per FR-ES-010 — occurs before, not only after, retrieval, so an unauthorized query against a restricted scope fails fast. |
| 4 | Query Rewriting | See below — the search-specific rewriting technique set. |
| 5 | Retriever Selection | Reuses [53_Query_Planning.md](53_Query_Planning.md)'s strategy-selection logic, tuned for human-scannable ranking rather than reasoning-context assembly. |
| 6 | Hybrid Retrieval | Reuses [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s retrieval strategies and signal composition. |
| 7 | Ranking | See [72_Search_Ranking.md](72_Search_Ranking.md). |
| 8 | Deduplication | Per FR-RT-004's pattern, applied to the human-facing result list. |
| 9 | Citation Mapping | Attaches source attribution to each result (per [57_Citation_Engine.md](57_Citation_Engine.md)'s field structure), not a full AI-generated citation-per-claim since no claim synthesis occurs in Enterprise Search. |
| 10 | Confidence Estimation | A per-result confidence indicator (per [58_Confidence_Engine.md](58_Confidence_Engine.md)'s factor model, applied per search result rather than per AI answer). |
| 11 | Response Formatting | Constructs the final search response payload — a ranked, structured list of results per [70_Enterprise_Search.md](70_Enterprise_Search.md) and this document's Search Result Requirements below. This is presentation-shaping, not natural-language answer synthesis; the Search Pipeline never invokes the AI Reasoning Layer ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)). |

### Distinction from the AI Request Lifecycle

This pipeline shares stages 4–8 (Query Rewriting through Deduplication) with the AI Request Lifecycle's corresponding stages, since both consume the same underlying Retrieval Architecture. It diverges at the endpoint: the AI Request Lifecycle proceeds through Context Assembly, Prompt Construction, LLM Invocation, and Reasoning (per [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) to produce a synthesized answer; the Search Pipeline stops at a ranked, citable result list, formatted for direct human review. A user's single query may, depending on the interface they used to issue it, invoke either pipeline — the Conversation Domain invokes the AI Request Lifecycle; the Enterprise Search Domain's search interface invokes this Search Pipeline — but the underlying retrieval mechanics are shared, not duplicated.

## Query Rewriting (Search-Specific)

Enterprise Search SHALL support the following nine rewriting techniques — a search-tuned subset and slight variation of [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s ten AI-reasoning-facing techniques, omitting Query Decomposition (which serves multi-step reasoning, not a single ranked result list) and adding Pluralization and Query Normalization (which matter more for keyword-index matching than for reasoning-context retrieval):

| Technique | Notes |
|---|---|
| Synonym Expansion | Shared with [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md). |
| Abbreviation Expansion | Shared. |
| Acronym Resolution | A search-specific refinement of Abbreviation Expansion, distinguishing acronyms (e.g., "API") from general abbreviations. |
| Technology Aliases | Shared. |
| Department Aliases | Shared. |
| Spell Correction | Shared. |
| Entity Resolution | Shared. |
| Pluralization | New here — normalizing singular/plural term variants for keyword index matching (e.g., "policy"/"policies"), more directly relevant to BM25-style matching than to semantic retrieval. |
| Query Normalization | New here — general text normalization (case, whitespace, punctuation) before index lookup. |

## Autocomplete

Enterprise Search SHALL support the following six autocomplete suggestion types, directly implementing FR-ES-007:

| Suggestion Type | Source |
|---|---|
| Entity Suggestions | Knowledge Graph Domain entities matching the partial input. |
| Document Suggestions | Document titles matching the partial input. |
| Project Suggestions | Project entities matching the partial input. |
| Technology Suggestions | Technology entities matching the partial input. |
| Department Suggestions | Team/Department metadata matching the partial input. |
| User Suggestions | User names matching the partial input, supporting Expert Search initiation. |

All six suggestion types are subject to Permission-Aware filtering per the same rule as full search results — a suggestion never reveals the existence of content or entities the requesting user cannot access, per FR-ES-007's acceptance criteria and [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Permission-aware Retrieval.

## Filtering

Enterprise Search SHALL support filtering by the following thirteen dimensions, directly implementing FR-ES-004:

Workspace, Department, Project, Author, Owner, Tags, Date, Document Type, Connector, Knowledge Source, Language, File Type, Custom Metadata.

Each dimension corresponds to a Metadata Extraction field ([69_Metadata_Extraction.md](69_Metadata_Extraction.md)) or a structural identifier (Workspace, Connector, Knowledge Source) already established in the Canonical Data Model ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) — no new metadata field is introduced solely for filtering purposes; filtering is a query operation over already-captured metadata.

## Search Result Requirements

Every search result SHALL include the following ten fields:

| Field | Source |
|---|---|
| Title | [69_Metadata_Extraction.md](69_Metadata_Extraction.md) |
| Summary | Knowledge Processing's enrichment output (FR-KP-006), or a generated snippet where no summary exists. |
| Source | [69_Metadata_Extraction.md](69_Metadata_Extraction.md)'s Source System field. |
| Connector | The specific Connector Instance ([67_Connector_Lifecycle.md](67_Connector_Lifecycle.md)) that synced this content. |
| Confidence | Per stage 10 of this pipeline. |
| Metadata | The full structural metadata set ([69_Metadata_Extraction.md](69_Metadata_Extraction.md)). |
| Permission Status | Confirms the result's inclusion has already passed Permission Validation (stage 3) — surfaced for transparency, not as a re-check. |
| Last Updated | [69_Metadata_Extraction.md](69_Metadata_Extraction.md)'s Modified Date. |
| Relevant Snippet | The specific passage matching the query, distinct from the general Summary. |
| Citation | Per stage 9, formatted per [57_Citation_Engine.md](57_Citation_Engine.md). |

## Responsibilities

- Every new Search Type added per [70_Enterprise_Search.md](70_Enterprise_Search.md) must flow through this same eleven-stage pipeline — a Search Type requiring a fundamentally different pipeline shape would indicate it is not actually a search type but a distinct capability warranting its own architecture.
- Query Rewriting techniques shared between this document and [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) must be implemented once and reused, not duplicated as separate implementations that could drift apart in behavior.

## Constraints

- This document does not specify the autocomplete latency target — see Open Question 27 in [27_Open_Questions.md](27_Open_Questions.md), still open.
- This document does not specify the exact snippet-extraction algorithm — Deferred to Architecture.

## Future Considerations

- As Query Rewriting techniques prove effective in one pipeline, their applicability to the other (AI Request Lifecycle vs. Search Pipeline) should be periodically reassessed, since the two pipelines' shared foundation means improvements often transfer.

## Acceptance Criteria

- [ ] All eleven Search Pipeline stages from the governing specification are defined, with the distinction from the AI Request Lifecycle made explicit.
- [ ] All nine search-specific Query Rewriting techniques from the governing specification are defined, with shared vs. new-to-search techniques distinguished.
- [ ] All six Autocomplete suggestion types from the governing specification are defined, with permission-awareness stated as binding.
- [ ] All thirteen Filtering dimensions and ten Search Result Requirements fields from the governing specification are defined.
