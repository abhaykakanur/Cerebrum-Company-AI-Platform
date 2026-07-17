# 63 — AI Guardrails

## Purpose

This document defines the safety architecture governing the AI subsystem: the nine enforcement areas that prevent the AI from becoming a vector for permission bypass, data leakage, or manipulation. It elaborates the Security Overview in [30_System_Architecture.md](30_System_Architecture.md) and the Security Domain architecture in [35_Domain_Architecture.md](35_Domain_Architecture.md), specifically as they apply to the AI Request Lifecycle.

## Scope

This document covers AI-specific safety enforcement. It does not redefine platform-wide security architecture (encryption, secrets management, tenant isolation — see [30_System_Architecture.md](30_System_Architecture.md)'s Security Overview, [46_Multi_Tenancy.md](46_Multi_Tenancy.md), [48_Data_Integrity.md](48_Data_Integrity.md)) beyond how the AI subsystem specifically consumes and reinforces those guarantees.

## Definitions

- **Prompt Injection** — An attack where content within retrieved Evidence (or, less commonly, the user query itself) is crafted to be interpreted as an instruction by the LLM rather than as data, potentially causing the AI to disregard its System Instructions or Safety Constraints.
- **Context Isolation** — The guarantee that one request's Assembled Context never leaks into or influences another, concurrent or subsequent, unrelated request.
- **Secret Detection Readiness** — Architectural preparedness to detect and redact credential-shaped content (API keys, passwords) appearing in retrieved Evidence before it reaches a prompt or a response.

## The Nine Guardrail Enforcement Areas

The AI SHALL enforce the following nine safety areas on every request:

### 1. Permission-Aware Retrieval

Already established as binding in [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) — every retrieval strategy is filtered by the requesting user's Authorization Layer permissions before content becomes eligible for Context Assembly. This guardrail is stated here as the AI subsystem's first and most fundamental line of defense: content the AI never retrieves cannot leak, regardless of any downstream prompt manipulation.

### 2. Prompt Injection Resistance

Building on [55_Prompt_Construction.md](55_Prompt_Construction.md)'s "no hidden prompt logic" rule, Prompt Construction SHALL structurally delineate retrieved Evidence as data, never as instruction — every piece of retrieved content is wrapped with explicit boundary markers (Deferred to Architecture for the specific mechanism) that the System Instructions direct the model to treat as untrusted, quotable data rather than directives. This is the primary defense against a malicious or compromised document instructing the AI, via its own content, to ignore its grounding requirements or reveal information outside the current request's permission scope.

### 3. Context Isolation

Every request's Assembled Context ([54_Context_Assembly.md](54_Context_Assembly.md)) is constructed fresh, scoped to that request's Tenant ID, Workspace ID, and requesting actor — no caching or reuse mechanism SHALL share Assembled Context across two different users' requests, even within the same organization, and no mechanism SHALL carry Assembled Context across a Tenant ID boundary under any circumstance, per [46_Multi_Tenancy.md](46_Multi_Tenancy.md).

### 4. Tenant Isolation

Directly inherited from [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s per-datastore isolation mechanisms — the AI subsystem introduces no new isolation boundary but is bound by every existing one: Retrieval's Qdrant/Neo4j/OpenSearch queries, Memory Layer's PostgreSQL reads, and LLM Invocation's outbound provider calls (which never transmit cross-tenant content in a single request) all respect tenant scoping.

### 5. Citation Validation

Per [57_Citation_Engine.md](57_Citation_Engine.md)'s Permission Validation field — every citation is re-validated for the requesting user's access at generation and display time, preventing a scenario where cached or memory-derived content references a source the current user is not authorized to view.

### 6. Sensitive Data Protection

Content classified as sensitive (via Knowledge Processing's metadata enrichment, FR-KP-006, or explicit tagging, FR-DM-004) SHALL be eligible for retrieval only under the same Authorization Layer permission checks as any other content — no separate sensitivity bypass exists — but SHALL additionally be excluded from lower-trust contexts where architecturally applicable (e.g., excluded from Query Rewriting's Context Completion step if doing so would leak sensitive content into an autocomplete-style suggestion visible before full permission re-evaluation, Deferred to Architecture for the specific mechanism).

### 7. Restricted Document Handling

Documents marked with elevated restriction (e.g., legal-hold content per Open Question 58 in [49_Open_Questions.md](49_Open_Questions.md), or explicitly restricted-distribution policies) SHALL be retrievable for reasoning only when the requesting user's permission explicitly covers the restriction tier, not merely general workspace access — this is a stricter test than ordinary Authorization Layer resource-scoped permission, requiring the restriction tier itself to be a checked attribute.

### 8. PII Awareness

Retrieved Evidence containing personally identifiable information SHALL be handled per the same Authorization Layer permission model as any other content (no separate PII-specific access path), but Response Generation ([56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)) SHALL be architecturally capable of recognizing PII in Evidence and reflecting applicable handling requirements in the response (e.g., not restating a full identifier unnecessarily) — the specific detection technique and handling policy are Deferred to Architecture, tracked in [64_Open_Questions.md](64_Open_Questions.md).

### 9. Secret Detection Readiness

The architecture SHALL be prepared to detect credential-shaped content (API keys, passwords, tokens) in retrieved Evidence — such as a document accidentally containing a hard-coded credential — before it reaches a prompt or a response, mirroring the redaction discipline already required for logging in [38_Observability.md](38_Observability.md). "Readiness" acknowledges detection accuracy is imperfect; the guardrail's minimum bar is that Knowledge Processing's quality/classification pipeline (FR-KP-006) flags likely-credential content for exclusion from AI-facing retrieval, not that every possible secret is caught with certainty.

## Binding Rules

- **No prompt SHALL bypass enterprise permissions.** This is the single sentence that governs all nine areas above — every guardrail exists to make this sentence true under adversarial as well as ordinary conditions.
- **The AI SHALL refuse requests that violate authorization rules.** Where a query, however phrased, would require the AI to act outside the requesting user's Authorization Layer permissions, the correct response is an explicit refusal (structured per [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)'s Missing Information / explicit-unknown pattern), never a best-effort attempt that might leak unauthorized content.

## Interaction with Other Part 5 Documents

| Guardrail Area | Primary Enforcement Point |
|---|---|
| Permission-Aware Retrieval | [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md) |
| Prompt Injection Resistance | [55_Prompt_Construction.md](55_Prompt_Construction.md) |
| Context Isolation | [54_Context_Assembly.md](54_Context_Assembly.md) |
| Tenant Isolation | [46_Multi_Tenancy.md](46_Multi_Tenancy.md) (Part 4) |
| Citation Validation | [57_Citation_Engine.md](57_Citation_Engine.md) |
| Sensitive Data Protection, Restricted Document Handling, PII Awareness, Secret Detection Readiness | Knowledge Processing Domain metadata enrichment ([35_Domain_Architecture.md](35_Domain_Architecture.md), Part 3), enforced at retrieval eligibility |

## Responsibilities

- Every new AI capability introduced in a later phase must be evaluated against all nine guardrail areas before release — a capability that has not been explicitly checked against Prompt Injection Resistance and Permission-Aware Retrieval, in particular, is not production-ready regardless of its functional completeness.
- Security testing (per FR-SC-004 and [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s responsibilities) SHALL include adversarial prompt-injection testing using content deliberately crafted to attempt instruction override, not only functional correctness testing.

## Constraints

- This document does not specify the exact technique for detecting prompt injection attempts, PII, or secrets — Deferred to Architecture, tracked in [64_Open_Questions.md](64_Open_Questions.md).
- "Readiness" language (Secret Detection Readiness) is used deliberately where perfect detection is not architecturally guaranteeable — this document does not overstate the guardrail's certainty.

## Future Considerations

- As prompt injection techniques evolve, the boundary-marking mechanism in Prompt Injection Resistance should be periodically reassessed against known attack patterns, ideally informed by the Evaluation Layer's ([61_AI_Evaluation.md](61_AI_Evaluation.md)) tracked incident data once such incidents are observed and logged.

## Acceptance Criteria

- [ ] All nine guardrail enforcement areas from the governing specification are defined with a concrete mechanism or enforcement point.
- [ ] The "no prompt shall bypass permissions" and "AI shall refuse unauthorized requests" rules are stated as binding and unconditional.
- [ ] Every guardrail area is cross-referenced to its primary enforcement point elsewhere in the Part 5 (or Part 3/4) document set, avoiding duplicate specification.
