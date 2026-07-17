# 64 — Open Questions (CES Phase 0, Part 5)

## Purpose

This document records AI-architecture-specific ambiguities surfaced while writing [50_AI_Architecture.md](50_AI_Architecture.md) through [63_AI_Guardrails.md](63_AI_Guardrails.md). It extends, and does not replace, [11_Open_Questions.md](11_Open_Questions.md) (Part 1), [27_Open_Questions.md](27_Open_Questions.md) (Part 2), [40_Open_Questions.md](40_Open_Questions.md) (Part 3), and [49_Open_Questions.md](49_Open_Questions.md) (Part 4). Per the governing specification's instruction, implementation ambiguity is recorded here — with question, reason, impact, recommended alternatives, and an explicit statement that an architect decision is required — rather than invented.

## Scope

This document covers ambiguities in AI subsystem design left unresolved by documents 50–63. Numbering continues from [49_Open_Questions.md](49_Open_Questions.md) to maintain one unified backlog across all five CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

### 67 — Prompt Injection Boundary-Marking Mechanism

- **Question:** What specific mechanism delineates retrieved Evidence as untrusted data versus instruction within a constructed prompt (e.g., XML-style tags, a structured message-role separation, a dedicated data field distinct from the instruction field)?
- **Reason:** [55_Prompt_Construction.md](55_Prompt_Construction.md) and [63_AI_Guardrails.md](63_AI_Guardrails.md) both require this delineation to exist but defer the technique, since it is provider- and model-capability-dependent.
- **Impact:** Directly affects Prompt Injection Resistance's real-world effectiveness; a weak mechanism leaves the guardrail nominal rather than actual.
- **Recommended Alternatives:** (a) Structured message-role separation where the provider API supports it (system/user/data roles); (b) explicit delimiter tags with instruction to disregard delimited content as directives; (c) a hybrid combining both, chosen per active provider.
- **Architect Decision Required:** Yes, before Prompt Construction implementation begins.

### 68 — PII Detection Technique and Handling Policy

- **Question:** What technique detects PII in retrieved Evidence, and what is the specific handling policy once detected (redact, flag, restrict retrieval entirely)?
- **Reason:** [63_AI_Guardrails.md](63_AI_Guardrails.md) requires PII Awareness but explicitly defers both the detection technique and the handling policy.
- **Impact:** Affects compliance posture (Open Question 11 in [11_Open_Questions.md](11_Open_Questions.md)) and response quality (over-aggressive redaction degrades usefulness).
- **Recommended Alternatives:** (a) A dedicated PII-detection model/library integrated into Knowledge Processing's enrichment stage; (b) provider-native PII detection where available; (c) policy-only approach relying on Authorization Layer scoping without automated detection.
- **Architect Decision Required:** Yes, with legal/compliance input given the regulatory dimension.

### 69 — Secret Detection Technique

- **Question:** What technique flags credential-shaped content (API keys, tokens, passwords) in retrieved Evidence for exclusion from AI-facing retrieval?
- **Reason:** [63_AI_Guardrails.md](63_AI_Guardrails.md)'s Secret Detection Readiness is stated as an architectural minimum without a specific detection mechanism.
- **Impact:** A credential accidentally present in an ingested document could otherwise be surfaced in a response, a security incident distinct from ordinary hallucination risk.
- **Recommended Alternatives:** (a) Pattern-based detection (regex for known credential shapes) at Knowledge Processing time; (b) a dedicated secret-scanning library; (c) both, layered.
- **Architect Decision Required:** Yes, before general availability, given the security severity.

### 70 — Query/Intent Classification Technique

- **Question:** Is Intent Analysis and Query Classification (stages 4–5 of [51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) performed by a rule-based system, a lightweight classification model, or the primary LLM itself as a preliminary call?
- **Reason:** The lifecycle document defines the stages and their < 100 ms target but does not commit to an implementation approach, which has direct latency and cost implications.
- **Impact:** Directly affects the Intent Classification performance target's achievability — an LLM-based classifier is unlikely to meet a 100 ms target; a rule-based or lightweight-model approach is more plausible but may sacrifice classification accuracy on ambiguous queries.
- **Recommended Alternatives:** (a) A small, fast, locally-hosted classification model; (b) rule-based heuristics with an LLM fallback only for `Unknown Query` cases; (c) embedding-similarity classification against labeled example queries.
- **Architect Decision Required:** Yes, given the direct performance-target tension.

### 71 — Default AI Configuration Values

- **Question:** What are the default values for Temperature, Maximum Tokens, Confidence Threshold, and Retrieval Limits ([62_AI_Governance.md](62_AI_Governance.md))?
- **Reason:** The governance document defines these as configurable settings without proposing defaults, consistent with this phase's "specify, do not implement" scope.
- **Impact:** Affects out-of-the-box behavior for organizations that do not customize configuration.
- **Recommended Alternatives:** Establish conservative defaults (lower temperature, stricter confidence threshold) for initial general availability, with organizations opting into more permissive settings deliberately.
- **Architect Decision Required:** Yes, informed by initial Evaluation Layer benchmark results.

### 72 — Default and Fallback Provider Selection

- **Question:** Which provider is the platform default, and what is the default fallback chain?
- **Reason:** [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md) supports seven provider categories without designating a default, consistent with Open Question 10 in [11_Open_Questions.md](11_Open_Questions.md) and Open Question 42 in [40_Open_Questions.md](40_Open_Questions.md), which this question directly extends with the fallback-chain specificity now that the fallback *policy* (organization-configurable) is decided.
- **Impact:** Affects new-organization onboarding experience and cost baseline.
- **Recommended Alternatives:** Deferred to a vendor/commercial evaluation outside this specification's scope.
- **Architect Decision Required:** Yes, likely a business/procurement decision as much as a technical one.

### 73 — Context Compression Technique

- **Question:** What specific technique performs Context Compression ([54_Context_Assembly.md](54_Context_Assembly.md)) while preserving citation eligibility — extractive summarization, a smaller model-based compression pass, or a non-AI heuristic (e.g., sentence-importance scoring)?
- **Reason:** The document requires the capability and its citation-preservation constraint without specifying the technique.
- **Impact:** Affects the fidelity/token-savings tradeoff and the risk of silently degrading grounding quality.
- **Recommended Alternatives:** (a) Extractive-only compression (removing whole sentences rather than paraphrasing, minimizing fidelity risk); (b) a dedicated compression model; (c) no compression in V1.0, relying solely on Chunk Prioritization and truncation.
- **Architect Decision Required:** Yes; option (c) is a reasonable initial simplification pending evidence that compression is necessary.

### 74 — Code-Aware and Whole-Document Embedding Model Policy

- **Question:** When is a code-aware embedding model used versus the standard natural-language model, and when is whole-document (versus only Chunk-level) embedding actually generated, given it is listed as supported but not mandatory for every document?
- **Reason:** [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)'s Embedding Strategy lists both capabilities without a triggering policy.
- **Impact:** Affects retrieval quality for Code Query classifications and storage/compute cost for whole-document embeddings.
- **Recommended Alternatives:** (a) Code-aware embedding triggered by connector category (GitHub/GitLab) or detected content-type classification; (b) whole-document embedding generated only for documents below a size threshold where chunk-level retrieval alone underperforms.
- **Architect Decision Required:** Yes, informed by early Retrieval Precision/Recall data per document type.

### 75 — Sensitive-Context Exclusion Mechanism in Query Rewriting

- **Question:** What specific mechanism prevents sensitive content from leaking into Query Rewriting's Context Completion step (which draws on Memory) before full permission re-evaluation occurs?
- **Reason:** [63_AI_Guardrails.md](63_AI_Guardrails.md)'s Sensitive Data Protection flags this as a specific risk without resolving the mechanism.
- **Impact:** A gap here could allow sensitive content to influence query rewriting even if it is later correctly excluded from the final response's citations.
- **Recommended Alternatives:** (a) Apply full Authorization Layer filtering to Memory content before it is eligible for Context Completion, not only at final Context Assembly; (b) exclude sensitivity-flagged content from Memory-sourced Context Completion entirely, regardless of permission.
- **Architect Decision Required:** Yes, given the security sensitivity.

### 76 — Restriction Tier Model

- **Question:** What is the concrete data model for "restriction tiers" referenced in [63_AI_Guardrails.md](63_AI_Guardrails.md)'s Restricted Document Handling — a fixed enumeration (e.g., Standard/Confidential/Restricted), a flexible tagging system, or an extension of the Authorization Domain's existing permission model?
- **Reason:** The guardrail requires a stricter-than-ordinary check without defining what it checks against.
- **Impact:** Affects both the Authorization Domain's data model (Part 2/3) and Knowledge Processing's classification metadata (Part 3).
- **Recommended Alternatives:** Extend the existing resource-scoped permission model (FR-AUTZ-003) with a restriction-tier attribute, rather than introducing a parallel access-control system.
- **Architect Decision Required:** Yes, coordinated with Open Question 58 (legal hold mechanics) in [49_Open_Questions.md](49_Open_Questions.md), since both concern elevated-sensitivity content handling.

### 77 — Automated Benchmark Test-Set Composition and Maintenance

- **Question:** How is the automated benchmark test-set ([61_AI_Evaluation.md](61_AI_Evaluation.md)) initially composed, and what process keeps it representative as Cerebrum's connector coverage and query patterns evolve?
- **Reason:** The document requires the benchmark's existence without specifying its curation process.
- **Impact:** A stale or unrepresentative benchmark gives false confidence in Grounding Accuracy/Hallucination Rate stability.
- **Recommended Alternatives:** (a) Seed from early Human Review-flagged real queries (anonymized); (b) synthetic query generation per Query Classification category, ensuring coverage of all nineteen classifications.
- **Architect Decision Required:** Yes, as an operational process design, not purely technical.

### 78 — Human Review Sampling Rate and Reviewer Qualification

- **Question:** What proportion of responses undergo Human Review, and what qualifies a reviewer (domain expertise requirement, training)?
- **Reason:** [61_AI_Evaluation.md](61_AI_Evaluation.md) requires Human Review for Response Helpfulness, Response Correctness, and Retrieval Recall without specifying sampling rate or reviewer qualification.
- **Impact:** Affects both evaluation statistical validity and operational cost.
- **Recommended Alternatives:** Stratified sampling weighted toward low-confidence and user-flagged responses, reviewed by subject-matter-adjacent staff rather than a generic QA team, given the organizational-knowledge-specific nature of correctness assessment.
- **Architect Decision Required:** Yes, as an operational process design.

### 79 — Confidence Score Formula and Factor Weighting

- **Question:** What is the specific formula combining the nine Confidence Factors ([58_Confidence_Engine.md](58_Confidence_Engine.md)) into a single score, and what is each factor's relative weight?
- **Reason:** Directly extends Open Question 6 in [11_Open_Questions.md](11_Open_Questions.md), now with nine named factors requiring explicit weighting rather than an unspecified scoring mechanism in the abstract.
- **Impact:** Directly determines Confidence Calibration quality and, downstream, how often FR-CF-003's low-confidence handling triggers.
- **Recommended Alternatives:** (a) An initial hand-tuned linear weighting, revised using Confidence Calibration feedback (FR-CF-004) once real data exists; (b) a learned weighting model trained on Human Review-labeled correctness outcomes, once sufficient labeled data accumulates.
- **Architect Decision Required:** Yes; option (a) is the pragmatic starting point pending option (b)'s data prerequisite.

### 80 — Memory Freshness Time-to-Live Per Category

- **Question:** What is the specific freshness time-to-live for each of the nine Memory Categories ([59_Memory_Architecture.md](59_Memory_Architecture.md)), particularly the four new request-scoped categories (User Preference, Workspace/Task/Domain Context) not backed by an existing Enterprise Memory Domain freshness signal?
- **Reason:** The document mandates freshness evaluation before every request without specifying category-level durations.
- **Impact:** Too-short a TTL degrades conversational coherence (re-deriving context repeatedly); too-long a TTL risks the stale-memory failure mode the document itself warns against.
- **Recommended Alternatives:** Conversation-scoped categories (Task Context) expire with the conversation session; organization-durable categories (Domain Context) use a longer, periodically-refreshed TTL.
- **Architect Decision Required:** Yes, likely tunable per category via [62_AI_Governance.md](62_AI_Governance.md)'s Evaluation Settings pattern rather than fixed globally.

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Questions 67–69 (Prompt Injection, PII, Secret Detection) carry security severity and should be prioritized before general availability, not treated as post-launch refinements.

## Constraints

- This list reflects ambiguities identifiable from the Part 5 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 50–63 rises to the level of a tracked open question here — routine, low-risk implementation latitude is intentionally not tracked.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the pattern in Parts 1–4's Open Questions documents) with a link to the governing ADR.
- Given the number of Part 5 questions with direct security implications (67, 68, 69, 75, 76), a dedicated AI security review — beyond the general Security Domain review referenced in [30_System_Architecture.md](30_System_Architecture.md) — is recommended before architecture-implementation work on the AI subsystem begins.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question includes Question, Reason, Impact, Recommended Alternatives, and an explicit Architect Decision Required statement, per the governing specification's format.
- [ ] No question duplicates a question already recorded in [11_Open_Questions.md](11_Open_Questions.md), [27_Open_Questions.md](27_Open_Questions.md), [40_Open_Questions.md](40_Open_Questions.md), or [49_Open_Questions.md](49_Open_Questions.md) without adding AI-architecture-level specificity.
