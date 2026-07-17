# 89 — AI Chat Architecture

## Purpose

This document defines the AI Chat frontend's capabilities and maps each to the backend AI Subsystem Layer ([50_AI_Architecture.md](50_AI_Architecture.md)) that provides it, ensuring the Chat UI is a faithful, thin presentation of the AI Request Lifecycle ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) rather than a reimplementation of any of its logic.

## Scope

This document covers the AI Chat UI's feature set and its backend mapping. It does not redefine AI Reasoning, Citation, or Confidence architecture — see Part 5 — or Conversation Domain data structure — see [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md).

## Definitions

See [10_Glossary.md](10_Glossary.md) and [50_AI_Architecture.md](50_AI_Architecture.md). No new terms are introduced here.

## AI Chat Capabilities

| Capability | Backend Mapping |
|---|---|
| Streaming responses | [31_Component_Architecture.md](31_Component_Architecture.md)'s AI Layer streaming pattern; the specific transport (SSE vs. WebSocket) remains Open Question 45 in [40_Open_Questions.md](40_Open_Questions.md). |
| Markdown | [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)'s Supported Output Formats, rendered via the Markdown Viewer component ([87_Component_Library.md](87_Component_Library.md)). |
| Tables | Same Output Formats list, rendered via the Data Grid or a lighter-weight table primitive. |
| Code blocks | Rendered via the Code Viewer component, using the JetBrains Mono token ([86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)). |
| Citations | [57_Citation_Engine.md](57_Citation_Engine.md)'s seven required citation fields, rendered inline or as a reference list (Deferred to Architecture for the specific presentation), each navigable per FR-CT-002. |
| Confidence indicator | [58_Confidence_Engine.md](58_Confidence_Engine.md)'s Confidence Score, always visibly presented per FR-CF-002 — never hidden behind an additional click, consistent with that requirement's binding acceptance criterion. |
| Conversation history | FR-CV-003, rendered as a navigable list per the Sidebar Layout element ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)). |
| Rename | New UI capability over the Conversation entity ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) — a metadata update, not requiring a new backend domain capability beyond a standard Conversation update operation. |
| Delete | Follows the Soft Delete Strategy ([47_Data_Governance.md](47_Data_Governance.md)) applied to the Conversation entity. |
| Pin | New UI-facing preference, likely backed by User Preference Memory ([59_Memory_Architecture.md](59_Memory_Architecture.md)) rather than a new domain. |
| Search | Searches within Conversation History, per [70_Enterprise_Search.md](70_Enterprise_Search.md)'s Conversation Search type. |
| Export | FR-CV-004, preserving citations per that requirement's binding acceptance criterion. |
| Suggested follow-ups | FR-CV-005, grounded in available content per that requirement's constraint. |
| Regenerate | Re-invokes the AI Request Lifecycle ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md)) for the same query, producing a new `Message` ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) rather than mutating the original — consistent with Messages being immutable once created per that document's entity definition. |
| Feedback | FR-CF-004's Confidence Calibration Feedback Loop — the UI surface for a user to indicate an answer was correct or useful. |

## Confidence and Citation Presentation Requirements

Two capabilities carry binding presentation requirements directly from Part 5, restated here as UI obligations:

- **Confidence indicator** must be visible with every response by default (FR-CF-002) — a UI design that requires a click-to-reveal for confidence would violate this requirement's "not available only on separate request" acceptance criterion.
- **Low-confidence responses** must be visibly, unambiguously labeled per FR-CF-003 — the Chat UI's low-confidence treatment (e.g., a distinct visual state using the Warning token, [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)) is not a cosmetic choice but a requirement-mandated behavior.

## Missing Information and Assumption Disclosure

Per [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)'s five-way distinction (Retrieved Facts / AI Inferences / Recommendations / Assumptions / Missing Information), the Chat UI SHALL visually distinguish these categories within a response — not render every sentence with identical visual treatment regardless of its evidentiary status. The specific visual treatment (e.g., distinct text styling, iconography) is Deferred to Architecture, but the underlying requirement that the distinction be visually recoverable, not only present in the underlying data, is binding.

## Responsibilities

- Every AI Chat capability must be verified against its backend requirement's acceptance criteria before being considered complete — a UI that renders a Confidence Score but not the low-confidence labeling behavior (FR-CF-003) is an incomplete implementation of the underlying requirement, not merely a cosmetic gap.
- The Chat UI must never compute or infer a confidence score, citation, or grounding assessment client-side — these are exclusively backend-computed values the UI presents, per the Thin Frontend rule ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)).

## Constraints

- This document does not specify the exact citation presentation format (inline marker vs. footnote vs. hyperlink) — Deferred to Architecture, per [57_Citation_Engine.md](57_Citation_Engine.md)'s own constraint.
- This document does not resolve the streaming transport mechanism — see Open Question 45 in [40_Open_Questions.md](40_Open_Questions.md), still open.

## Future Considerations

- As the Missing Information/Assumption visual treatment is designed, it should be validated with real users for comprehensibility — a distinction that exists in the data but is not intuitively understood in the UI would undermine the Explainability principle's actual goal despite being technically present.

## Acceptance Criteria

- [ ] All fourteen AI Chat capabilities from the governing specification are defined with their backend mapping.
- [ ] Confidence indicator and low-confidence labeling are stated as binding presentation requirements traced to FR-CF-002/003's specific acceptance criteria, not optional design choices.
- [ ] The five-way fact/inference/recommendation/assumption/missing-information distinction is required to be visually recoverable in the UI, not merely present in underlying data.
- [ ] The Chat UI is confirmed to never independently compute confidence, citation, or grounding — consistent with the Thin Frontend principle.
