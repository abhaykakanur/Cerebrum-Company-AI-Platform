# 56 — Reasoning Architecture

## Purpose

This document defines the Reasoning and Response Generation AI Subsystem Layers: the principles governing how Cerebrum reasons over retrieved evidence, the reasoning types it supports, and how reasoning output is shaped into a structured, presentable response. It elaborates FR-AR-001 through FR-AR-008 from [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Scope

This document covers reasoning principles, reasoning types, and response structure. It does not cover citation attachment (see [57_Citation_Engine.md](57_Citation_Engine.md)), confidence scoring or evidence validation (see [58_Confidence_Engine.md](58_Confidence_Engine.md)), or prompt construction that precedes reasoning (see [55_Prompt_Construction.md](55_Prompt_Construction.md)).

## Definitions

- **Reasoning Type** — A distinct pattern of inference over evidence, selected per the Query Plan's required reasoning strategy ([53_Query_Planning.md](53_Query_Planning.md)).
- **Chain-of-Evidence Reasoning** — A reasoning approach where each inferential step names the specific evidence supporting it, forming an inspectable chain from question to answer.

## Reasoning Principles

The reasoning engine SHALL adhere to the following eleven principles on every request, directly implementing the AI Design Philosophy from [50_AI_Architecture.md](50_AI_Architecture.md):

1. **Reason only over retrieved evidence.** No reasoning step may draw on model-internal knowledge not present in the Assembled Context when the query calls for organizational fact, per FR-AR-001.
2. **Never fabricate enterprise information.** The binding constraint the Validation Layer verifies post-hoc ([58_Confidence_Engine.md](58_Confidence_Engine.md)) — this principle states the generation-time intent it enforces.
3. **Prefer evidence over probability.** Where retrieved evidence and the model's own probabilistic prior conflict, evidence governs — this is the operational meaning of "the AI is never the source of truth."
4. **Prefer uncertainty over hallucination.** Directly implements the AI Design Philosophy's sixth rule — an explicit "I don't know" is the architecturally correct output when evidence is insufficient.
5. **Reference supporting evidence.** Every inferential step, not only the final answer, names the evidence it draws from — the foundation of Chain-of-Evidence Reasoning below.
6. **Detect contradictory evidence.** Directly implements Open Question 7 in [11_Open_Questions.md](11_Open_Questions.md)'s eventual resolution requirement — contradictions are surfaced, never silently resolved by picking one source.
7. **Support multi-document reasoning.** Per FR-AR-003, synthesizing across documents that individually only partially answer the query.
8. **Support chain-of-evidence reasoning.** See definition above; this is the mechanism realizing FR-AR-008's Reasoning Transparency.
9. **Support cross-reference reasoning.** Following a reference from one piece of evidence to another it points to (e.g., a Decision's Evidence Link to a Document).
10. **Support timeline reasoning.** Ordering evidence chronologically to answer "how did this evolve" questions (Timeline Query classification, [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)).
11. **Support dependency reasoning.** Traversing Knowledge Graph relationships to answer "what does this depend on / what depends on this" questions (FR-KG-006, UC-10).

## Supported Reasoning Types

The following thirteen reasoning types are supported, each a specific configuration of the eleven principles above applied to a particular query shape:

| Reasoning Type | Description | Typical Query Classification |
|---|---|---|
| Single Document Reasoning | Answer derivable from one retrieved document. | Document Lookup |
| Cross Document Reasoning | Answer requires synthesizing multiple documents. | Multi-document Query, Analytical Query |
| Temporal Reasoning | Answer requires chronological ordering/comparison. | Timeline Query |
| Relationship Reasoning | Answer requires traversing entity relationships. | Relationship Query |
| Dependency Reasoning | Answer requires identifying dependencies between entities. | Relationship Query (dependency-specific) |
| Decision Reasoning | Answer requires understanding a decision's rationale and context. | Decision Query |
| Architecture Reasoning | Answer requires technical architecture context. | Architecture Query |
| Policy Reasoning | Answer requires current-vs-superseded policy awareness (FR-EM-008). | Policy Query |
| Meeting Reasoning | Answer requires meeting-derived context. | Meeting Query |
| Comparative Reasoning | Answer requires comparing two or more things. | Comparison Query |
| Summarization | Answer condenses known content without introducing new claims. | Summarization |
| Explanation | Answer clarifies "why" or "how," not just "what." | Informational Query (explanatory subset) |
| Root Cause Analysis | Answer traces an outcome back to its originating cause(s). | Analytical Query, Incident-related queries |

**Extensibility:** New reasoning types SHALL be addable without architectural redesign, following the same registry-based extensibility pattern as the Query Classification taxonomy in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md).

## Response Generation

The Response Generation Layer SHALL:

- Generate responses only after retrieval has completed (never before Context Assembly, per the strict pipeline ordering in [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)).
- Never answer directly from model prior knowledge when enterprise evidence is required, per Reasoning Principle 1.
- Separate factual information from inferred information, explicitly distinguishing:
  - **Retrieved Facts** — Claims directly traceable to a specific piece of Evidence.
  - **AI Inferences** — Conclusions drawn by combining multiple pieces of Evidence, not stated verbatim in any single source.
  - **Recommendations** — Suggested actions, explicitly marked as the AI's suggestion rather than an organizational fact.
  - **Assumptions** — Points where the reasoning process had to assume something not directly evidenced, disclosed rather than silently absorbed into the answer.
  - **Missing Information** — Aspects of the question the retrieved evidence could not address, stated explicitly rather than omitted without comment.

### Response Qualities

Every response SHALL be:

| Quality | Meaning |
|---|---|
| Consistent | The same question, asked twice with unchanged underlying knowledge, yields materially consistent answers. |
| Grounded | Every factual claim traces to Evidence, per the AI Design Philosophy. |
| Concise when appropriate | Matches response length to query complexity — a simple factual question does not receive an essay. |
| Detailed when requested | Expands to full detail when the user's query or Query Plan's output format calls for it. |
| Permission-aware | Never includes content the requesting user is not authorized to see, per FR-AUTZ-003 enforced upstream at Retrieval. |
| Citation-aware | Every claim is citation-eligible, per [57_Citation_Engine.md](57_Citation_Engine.md). |
| Deterministic wherever possible | Given identical inputs, materially consistent output — bounded by the underlying LLM provider's own generation determinism, which Cerebrum's architecture does not fully control (Deferred to Architecture/provider capability). |

### Required Response Structure

Every response SHALL contain the following six elements:

| Element | Description |
|---|---|
| Primary Answer | The direct response to the user's question. |
| Supporting Evidence | The specific Evidence items the answer draws from. |
| Source Citations | Formatted per [57_Citation_Engine.md](57_Citation_Engine.md). |
| Confidence Level | Per [58_Confidence_Engine.md](58_Confidence_Engine.md). |
| Reasoning Summary | A brief account of how the answer was derived (which reasoning type, what evidence was combined), distinct from the full Reasoning Trace (FR-AR-008) available on request. |
| Relevant Related Knowledge | Adjacent information the user did not explicitly ask for but which the retrieved context surfaced as likely relevant, supporting the "generate knowledge summaries" and discovery-oriented use cases from [06_Use_Cases.md](06_Use_Cases.md). |

### Supported Output Formats

Consistent with FR-AR-007, responses SHALL support: Markdown, Bullet Lists, Tables, Code Blocks, Architecture Summaries, Executive Summaries, Technical Reports, Timeline Views, Decision Summaries, and Step-by-step Explanations — selected per the Query Plan's expected output format element ([53_Query_Planning.md](53_Query_Planning.md)). Every format, regardless of presentation structure, SHALL remain grounded in retrieved evidence per the Response Qualities above — format changes presentation, never the grounding requirement.

## Responsibilities

- Every new reasoning type proposed in a later phase must be defined against the eleven Reasoning Principles and added to the registry-based extensibility mechanism, not hard-coded as a special case.
- The five-way distinction (Retrieved Facts / AI Inferences / Recommendations / Assumptions / Missing Information) must be preserved in every response structure and output format — a format that cannot represent this distinction (e.g., a bare table with no room for hedging) is not a valid Response Generation output until adapted to carry it.

## Constraints

- This document does not specify the prompt phrasing used to elicit any of these behaviors from an LLM — Deferred to Architecture, explicitly out of scope per [55_Prompt_Construction.md](55_Prompt_Construction.md).
- Determinism claims are bounded by underlying provider capability, not a guarantee this architecture can make unconditionally.

## Future Considerations

- As Evaluation Layer data accumulates ([61_AI_Evaluation.md](61_AI_Evaluation.md)) on Response Correctness and Response Helpfulness per reasoning type, some reasoning types may warrant dedicated evaluation benchmarks given their differing failure modes (e.g., Root Cause Analysis's failure mode — an incorrect causal claim — differs materially from Summarization's — an incomplete summary).

## Acceptance Criteria

- [ ] All eleven Reasoning Principles from the governing specification are stated and connected to the AI Design Philosophy.
- [ ] All thirteen Supported Reasoning Types from the governing specification are defined, with extensibility addressed.
- [ ] Response Generation's fact/inference/recommendation/assumption/missing-information distinction, response qualities, and six-element structure are all fully represented.
- [ ] All ten supported output formats from the governing specification are listed, with the grounding requirement stated as format-independent.
