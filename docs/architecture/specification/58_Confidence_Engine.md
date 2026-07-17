# 58 — Confidence Engine

## Purpose

This document defines the Confidence and Validation AI Subsystem Layers: what factors determine a response's confidence score, and the hallucination-prevention mechanisms that make the AI Design Philosophy's "prefer uncertainty over hallucination" rule ([50_AI_Architecture.md](50_AI_Architecture.md)) architecturally real. It elaborates FR-CF-001 through FR-CF-004 and FR-AR-005/FR-AR-006 from [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Scope

This document covers confidence scoring and hallucination prevention together, since the latter is substantially implemented through the former (a response the system is not confident in is the trigger for uncertainty-acknowledgment behavior). It does not cover citation mechanics (see [57_Citation_Engine.md](57_Citation_Engine.md), whose verification outcome is a confidence input) or AI Guardrails' broader safety scope (see [63_AI_Guardrails.md](63_AI_Guardrails.md)).

## Definitions

- **Evidence Coverage** — The degree to which retrieved Evidence actually addresses every part of the user's question, as opposed to only a portion of it.
- **Graph Consistency** — Whether Knowledge Graph relationships relevant to the answer are internally consistent (no contradictory relationship types between the same entities).
- **Confidence Calibration** — The degree to which a stated confidence score matches the actual empirical likelihood the response is correct, per Open Question 6 in [11_Open_Questions.md](11_Open_Questions.md).

## Confidence Factors

Every AI response SHALL include internal confidence estimation, considering the following nine factors:

| Factor | What It Measures |
|---|---|
| Retrieval Score | The relevance/ranking strength of the retrieved Evidence, per [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Hybrid Retrieval scoring. |
| Source Agreement | Whether multiple independent sources corroborate the same claim. |
| Source Freshness | Per FR-EM-010's Memory Freshness Signal — how recently the cited content was confirmed accurate. |
| Source Authority | Per [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)'s Authority Signal — whether the source carries elevated organizational trust. |
| Graph Consistency | See definition above. |
| Document Consistency | Whether the cited document's content is internally consistent (not, for instance, a draft containing unresolved conflicting statements). |
| Contradictions | Whether Reasoning Principle 6 ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)) detected conflicting evidence for this claim. |
| Evidence Coverage | See definition above. |
| Missing Context | Whether Query Planning's data-source scoping ([53_Query_Planning.md](53_Query_Planning.md)) or retrieval's Partial Data Availability failure mode ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) left gaps. |

**Binding rule:** Confidence SHALL NEVER be based solely on model probability (e.g., an LLM's token-generation likelihood or self-reported certainty). Model-internal probability signals, where available from a given provider, MAY be one minor input, but the nine factors above — all derived from the retrieval and evidence layer, not the model's own generation process — SHALL dominate the confidence computation. This directly implements the AI Design Philosophy's "the AI is never the source of truth": if confidence were computed primarily from the model's own probability, the model would effectively be grading its own homework.

## Confidence Score Application

Per FR-CF-001 through FR-CF-004 (elaborated at the requirements level in Part 2, referenced here for AI-architecture completeness):

- Every response has a confidence indicator before being returned (FR-CF-001).
- Confidence is visibly presented with every response, not available only on request (FR-CF-002).
- A response below a configurable confidence threshold is visibly, unambiguously labeled as low confidence, with organization-level configuration of whether low-confidence responses are shown-with-warning or withheld (FR-CF-003, configured via [62_AI_Governance.md](62_AI_Governance.md)).
- User feedback on response correctness feeds a Confidence Calibration loop (FR-CF-004), tracked as an Evaluation Layer metric ([61_AI_Evaluation.md](61_AI_Evaluation.md)).

## Hallucination Prevention

The AI SHALL minimize hallucinations using the following eight mechanisms, several of which are cross-references to controls fully specified elsewhere — this section is their point of integration, not a duplicate specification:

| Mechanism | Specified In |
|---|---|
| Grounded Retrieval | [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) — only retrieved Evidence is eligible input to Reasoning. |
| Evidence Verification | This document (Validation Layer, below). |
| Citation Requirements | [57_Citation_Engine.md](57_Citation_Engine.md) — every claim must be citation-eligible. |
| Confidence Thresholds | This document, above. |
| Contradiction Detection | [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md), Reasoning Principle 6. |
| Missing Context Detection | This document's Confidence Factors (Evidence Coverage, Missing Context). |
| Permission Validation | [57_Citation_Engine.md](57_Citation_Engine.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Authorization Domain — hallucination prevention is not only about factual accuracy but about never fabricating access to content the response should not reveal. |
| Explicit Unknown Responses | [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)'s Response Generation — the architecturally sanctioned output when evidence is insufficient. |

**Binding rule:** When evidence is insufficient, the AI SHALL refuse to invent organizational knowledge. This is not a soft preference balanced against helpfulness — it is an absolute constraint, ranked above response completeness, directly implementing "hallucination is treated as a defect to be minimized, not an acceptable tradeoff" from [01_Product_Vision.md](01_Product_Vision.md).

## The Validation Layer

The Validation Layer performs Evidence Verification (stage 13 of [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)), executing after LLM Invocation and before Citation Generation:

1. Every claim in the generated response is checked against its associated Evidence — does the cited source actually support the claim, not merely relate to its topic?
2. A claim failing verification is either (a) revised to match what the Evidence actually supports, (b) removed from the response, or (c) explicitly downgraded to a stated Assumption ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)'s five-way distinction) — never returned unchanged and uncorrected.
3. Verification outcomes feed both Citation confidence ([57_Citation_Engine.md](57_Citation_Engine.md)) and the overall response Confidence Score (this document).
4. Verification outcomes are logged for Evaluation Layer tracking of Citation Accuracy and Hallucination Rate ([61_AI_Evaluation.md](61_AI_Evaluation.md)).

## Responsibilities

- Every new confidence factor proposed in a later phase must be justified against the binding rule that model probability never dominates — a proposed factor derived primarily from the model's own output (rather than the evidence/retrieval layer) requires an ADR explaining why it does not violate this rule.
- The Validation Layer's revise/remove/downgrade decision logic (step 2 above) must be applied to every claim, not sampled — partial validation undermines the entire hallucination-prevention architecture.

## Constraints

- This document does not specify the exact confidence-score formula (weighting across the nine factors) — Deferred to Architecture, tracked as Open Question 6 in [11_Open_Questions.md](11_Open_Questions.md).
- This document does not specify the default confidence threshold value — Deferred to Architecture, configured via [62_AI_Governance.md](62_AI_Governance.md).

## Future Considerations

- As Confidence Calibration data accumulates (FR-CF-004), the relative weighting of the nine confidence factors should be empirically tuned rather than left at an initial best-guess configuration, closing the loop between [61_AI_Evaluation.md](61_AI_Evaluation.md)'s Confidence Calibration metric and this document's scoring model.

## Acceptance Criteria

- [ ] All nine confidence factors from the governing specification are defined.
- [ ] The "never solely model probability" rule is stated as binding, with its rationale connected to the AI Philosophy.
- [ ] All eight hallucination-prevention mechanisms from the governing specification are addressed, each pointing to its full specification where one exists elsewhere.
- [ ] The explicit-refusal-when-insufficient-evidence rule is stated as absolute, not balanced against other concerns.
