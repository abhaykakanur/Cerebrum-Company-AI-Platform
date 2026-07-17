# 72 — Search Ranking

## Purpose

This document defines the ten signals Enterprise Search ranking considers, reconciling them with the Hybrid Retrieval signal composition already established in [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) (Part 5) and identifying which signals are new to the search-ranking context specifically.

## Scope

This document covers ranking signal definitions. It does not cover the retrieval mechanics that produce the candidate set ranking operates over (see [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) or the pipeline stage sequencing (see [71_Search_Pipeline.md](71_Search_Pipeline.md), whose stage 7 invokes this document's ranking model).

## Definitions

- **Ranking Signal** — A single, independently computable factor contributing to a result's overall rank position.
- **Popularity** — How frequently other users have engaged with (viewed, cited, clicked through to) a given item, distinct from its Authority (an intrinsic property of the source) or Recency (a timestamp-derived property).

## Ranking Signals

Ranking SHALL consider the following ten signals:

| Signal | Description | Relationship to [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Hybrid Retrieval |
|---|---|---|
| BM25 Score | Lexical relevance. | Shared — same signal, same computation. |
| Vector Similarity | Semantic relevance. | Shared — same signal, same computation. |
| Graph Distance | How close a result is, via Knowledge Graph traversal, to entities central to the query. | New here — a specific, named refinement of Hybrid Retrieval's "Knowledge Graph Traversal" signal, expressed as a distance metric for ranking purposes specifically. |
| Source Authority | Whether the source carries elevated organizational trust. | Shared — corresponds to Hybrid Retrieval's Authority Signals. |
| Recency | How recently the item was created or modified. | Shared — corresponds to Hybrid Retrieval's Recency Signals. |
| Popularity | See definition above. | New here — not present in [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s ten AI-reasoning-facing signals, since AI reasoning's evidentiary selection should not be biased by popularity the way human-facing search ranking legitimately can be (a frequently viewed document is a reasonable search-ranking boost; it is not evidence of factual correctness for AI grounding purposes). |
| Knowledge Freshness | Per FR-EM-010's Freshness Signal. | Shared — corresponds conceptually to Hybrid Retrieval's Recency Signal but is distinct: Recency is a raw timestamp; Knowledge Freshness incorporates confirmation/re-sync recency per [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Memory Freshness Signals. |
| Document Quality | Per FR-KP-010's Knowledge Quality Validation outcome. | Shared — corresponds to Hybrid Retrieval's Source Reliability signal. |
| Permission Match | Whether and how strongly the result matches the requesting user's permission scope (a hard filter, not merely a ranking boost, per FR-ES-010). | Shared — corresponds to Hybrid Retrieval's Permission Constraints, restated here as a ranking signal for clarity that permission match is always a floor (zero or excluded), never merely a boost. |
| Metadata Match | How well the result's structural metadata matches any active Filtering ([71_Search_Pipeline.md](71_Search_Pipeline.md)) or implicit query context. | Shared — corresponds to Hybrid Retrieval's Metadata Filtering signal. |

## Deliberate Divergence: Popularity

Popularity is the one signal in this document's ten with no counterpart in [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Hybrid Retrieval composition, and this is an intentional design decision, not an oversight: Popularity is a legitimate human-search-ranking signal (frequently consulted documents are often what a searching human wants) but would be an inappropriate input to AI Reasoning's evidence selection (a document's popularity says nothing about whether it is the *correct* evidence for a specific factual claim, and using it as a reasoning input risks systematically favoring commonly cited but potentially outdated or superseded content over accurate but less-viewed content). This divergence is recorded here explicitly so a future implementation does not assume the two signal sets must be identical.

## Weighting Configurability

Consistent with [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Hybrid Retrieval weighting configurability and FR-ES-003's acceptance criteria, the relative weighting between these ten ranking signals SHALL be configurable via [62_AI_Governance.md](62_AI_Governance.md)'s Search Configuration Management (FR-CG-002), independently of Hybrid Retrieval's own AI-reasoning-facing weighting — the two weighting configurations are tuned separately since they serve different consumers (human scanability vs. reasoning evidence quality) with different priorities.

## Responsibilities

- Any new ranking signal proposed in a later phase must be evaluated for whether it is appropriate for both human-facing ranking and AI-reasoning-facing retrieval, or ranking-specific only (following Popularity's precedent) — this evaluation must be explicit, not assumed.
- Permission Match must remain architecturally a hard filter (results below the permission floor are excluded entirely, never merely ranked lower) — conflating it with a soft-weighted signal would violate FR-ES-010.

## Constraints

- This document does not specify the exact ranking formula or default weights — Deferred to Architecture, configured via [62_AI_Governance.md](62_AI_Governance.md).
- This document does not specify how Popularity is measured (raw view count, click-through rate, citation frequency, or a composite) — Deferred to Architecture, informed by [73_Search_Analytics.md](73_Search_Analytics.md)'s tracked metrics.

## Future Considerations

- As Search Analytics data accumulates ([73_Search_Analytics.md](73_Search_Analytics.md)), ranking signal weights should be empirically tuned using observed Click-Through Rate outcomes, following the same calibration-loop pattern established for AI Confidence in [58_Confidence_Engine.md](58_Confidence_Engine.md).

## Acceptance Criteria

- [ ] All ten ranking signals from the governing specification are defined.
- [ ] Each signal's relationship to [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Hybrid Retrieval composition is explicit — shared, renamed/refined, or genuinely new.
- [ ] The Popularity signal's deliberate exclusion from AI-reasoning-facing retrieval is explained with its rationale, not left as an unexplained inconsistency.
- [ ] Permission Match is explicitly stated as a hard filter, not a soft-weighted signal.
