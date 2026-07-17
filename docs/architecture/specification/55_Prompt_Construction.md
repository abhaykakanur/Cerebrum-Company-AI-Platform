# 55 — Prompt Construction

## Purpose

This document defines how Assembled Context ([54_Context_Assembly.md](54_Context_Assembly.md)) is translated into the prompt submitted to an LLM Provider ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)). It establishes prompt construction as a deterministic, auditable process with no hidden logic capable of altering enterprise data.

## Scope

This document covers the architecture of prompt construction — its required contents and determinism guarantee. It does not contain any actual prompt text, template syntax, or model-specific formatting — that is implementation detail, explicitly out of scope for this specification per the governing document's "this is not a prompt library" statement.

## Definitions

- **Deterministic Prompt Construction** — Given identical inputs (query, Assembled Context, conversation state, configuration), prompt construction always produces the same prompt.
- **Hidden Prompt Logic** — Any prompt-construction behavior not visible in this architecture or in the Reasoning Transparency trace (FR-AR-008), particularly logic capable of writing to or altering enterprise data.

## Determinism Requirement

Prompt construction SHALL be deterministic. This is an architectural guarantee, not merely a preference: given the same Assembled Context, user question, conversation state, and AI configuration, the constructed prompt SHALL be byte-identical across repeated executions. This directly supports:

- **Reasoning Transparency (FR-AR-008):** A reasoning trace that includes the constructed prompt is only meaningful for debugging and audit if reconstructing it from the same inputs is reproducible.
- **Evaluation (FR-AL-003, [61_AI_Evaluation.md](61_AI_Evaluation.md)):** Comparing model behavior across evaluation runs requires holding prompt construction constant as a controlled variable.
- **Explicit over Implicit ([04_Project_Principles.md](04_Project_Principles.md)):** A non-deterministic prompt-construction step would hide behavior that must remain inspectable.

Determinism applies to prompt *construction* (the assembly of known inputs into a prompt string/structure); it does not imply the LLM's *output* is deterministic, which depends on provider- and model-specific generation settings ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md), [62_AI_Governance.md](62_AI_Governance.md)) outside this layer's control.

## Required Prompt Contents

Every constructed prompt SHALL contain the following nine elements, in a consistent structural arrangement:

| Element | Source | Purpose |
|---|---|---|
| System Instructions | AI Administration configuration ([62_AI_Governance.md](62_AI_Governance.md)) | Establishes the AI's role and the AI Design Philosophy's binding rules ([50_AI_Architecture.md](50_AI_Architecture.md)) as operative constraints for this request. |
| Enterprise Rules | AI Administration configuration | Organization- or workspace-specific behavioral rules (e.g., a stricter grounding requirement for a compliance-sensitive workspace, per FR-CG-001). |
| Retrieved Context | Assembled Context ([54_Context_Assembly.md](54_Context_Assembly.md)) | The evidentiary basis for a grounded answer. |
| Conversation Context | Conversation Domain (FR-CV-002) | Prior turns needed for follow-up coherence. |
| Relevant Memory | Memory Layer ([59_Memory_Architecture.md](59_Memory_Architecture.md)) | Non-expired contextual continuity. |
| User Question | The original (and, where applicable, rewritten — [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)) query. |
| Citation Instructions | Citation Layer requirements ([57_Citation_Engine.md](57_Citation_Engine.md)) | Directs the model to produce citation-eligible, attributable claims. |
| Output Format Instructions | Query Plan's expected output format ([53_Query_Planning.md](53_Query_Planning.md)) | Directs response structure (per [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)). |
| Safety Constraints | AI Guardrails ([63_AI_Guardrails.md](63_AI_Guardrails.md)) | Enforces permission boundaries and prompt-injection resistance at the prompt level, as one layer of defense among several. |

## No Hidden Prompt Logic

**Binding rule:** No prompt construction logic SHALL modify enterprise data. Prompt construction is a pure, read-only transformation: it reads Assembled Context, conversation state, and configuration, and produces a prompt — it never writes to the Knowledge Layer, never triggers a side effect in any domain, and never contains instructions that, if followed literally by the LLM, would cause a downstream system to mutate state without going through the standard, permission-checked Application Layer use cases defined in [34_Architecture_Principles.md](34_Architecture_Principles.md).

This rule exists specifically to prevent a class of failure where prompt content — especially content sourced from retrieved enterprise documents, which may themselves contain adversarial or malformed text — could be interpreted as an instruction rather than data. This is elaborated as Prompt Injection Resistance in [63_AI_Guardrails.md](63_AI_Guardrails.md); this document establishes the construction-time discipline (retrieved content is always clearly delineated as data, never concatenated into the instruction portion of the prompt) that makes that resistance possible.

## Responsibilities

- Every new prompt element proposed in a later phase must be added to the Required Prompt Contents table and justified against the AI Design Philosophy before implementation.
- Any proposed prompt-construction mechanism that reads from a source not listed here, or that could introduce non-determinism (e.g., including a live timestamp without controlling for it in evaluation), requires an ADR per [09_Governance.md](09_Governance.md).

## Constraints

- This document contains no prompt template text, no example prompts, and no model-specific formatting syntax — these are implementation details explicitly excluded from this specification.
- Determinism does not extend to LLM output generation, only to the construction of the prompt submitted for generation.

## Future Considerations

- As multiple AI Model Abstraction providers are supported ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)), prompt construction may need provider-specific formatting adapters (e.g., differing message-role conventions) — these adapters must preserve the same nine required contents and the same determinism guarantee, translating structure only, never altering substantive content.

## Acceptance Criteria

- [ ] Prompt construction's determinism requirement is stated as a binding architectural guarantee with a clear scope (construction, not generation).
- [ ] All nine required prompt contents from the governing specification are defined with their source and purpose.
- [ ] The "no hidden prompt logic" rule is connected to a concrete failure mode it prevents (prompt injection via retrieved content), not left as an abstract statement.
