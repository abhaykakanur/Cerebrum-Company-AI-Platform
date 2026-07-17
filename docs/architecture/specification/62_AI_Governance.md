# 62 — AI Governance

## Purpose

This document defines the AI Administration AI Subsystem Layer: what AI-related behavior is configurable by authorized administrators, and the versioning/auditability requirements on that configuration. It elaborates FR-CG-001 (AI Configuration Management) from [20_Functional_Requirements.md](20_Functional_Requirements.md) and the Configuration Domain architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md), specifically for AI-subsystem settings.

## Scope

This document covers what is configurable and how configuration is governed. It does not cover the general Configuration Layer architecture (environment variables, secrets, feature flags broadly — see [37_Configuration_Strategy.md](37_Configuration_Strategy.md)), which this document's AI-specific settings are a category within.

## Definitions

- **AI Configuration** — The subset of Configuration Domain settings ([35_Domain_Architecture.md](35_Domain_Architecture.md)) governing AI Subsystem Layer behavior, scoped at organization or workspace level per FR-OR-003's inheritance model.

## Configurable AI Settings

Administrators SHALL be able to configure the following thirteen settings, each subject to the Configuration Precedence order established in [37_Configuration_Strategy.md](37_Configuration_Strategy.md) (workspace override → organization default → configuration-file baseline → hard-coded default):

| Setting | Governs |
|---|---|
| Default Model | The primary LLM provider/model for LLM Invocation ([51_AI_Request_Lifecycle.md](51_AI_Request_Lifecycle.md) stage 12), per [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md). |
| Fallback Model | The secondary model attempted on Default Model failure, per [60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)'s fallback policy. |
| Embedding Model | The model used for Embedding Generation ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)). |
| Temperature | The generation randomness parameter passed to the active `LLMProviderPort` adapter — a provider-agnostic setting the abstraction layer translates per provider. |
| Maximum Tokens | The generation output length ceiling. |
| Context Window | The effective context size Cerebrum targets for a given model/provider combination, informing Token Management's Maximum Context Budget ([54_Context_Assembly.md](54_Context_Assembly.md)). |
| Retrieval Limits | The Maximum Retrieval Budget element of the Query Plan ([53_Query_Planning.md](53_Query_Planning.md)). |
| Confidence Threshold | The threshold below which a response is labeled low-confidence or withheld, per FR-CF-003 and [58_Confidence_Engine.md](58_Confidence_Engine.md). |
| Citation Requirements | Whether citation is mandatory-and-blocking (an uncited claim is suppressed) or advisory (an uncited claim is flagged but shown), per the strictness variation implied by [57_Citation_Engine.md](57_Citation_Engine.md) and [04_Project_Principles.md](04_Project_Principles.md)'s AI Philosophy. |
| Prompt Templates | The organization- or workspace-specific Enterprise Rules content injected into Prompt Construction ([55_Prompt_Construction.md](55_Prompt_Construction.md)) — never the System Instructions, which remain platform-controlled to preserve the AI Design Philosophy's binding rules ([50_AI_Architecture.md](50_AI_Architecture.md)) against override. |
| Feature Flags | AI-subsystem-specific feature gates (e.g., enabling a new Reasoning Type before general availability), per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s Feature Flag category. |
| Evaluation Settings | Automated benchmark cadence and human review sampling rate, per [61_AI_Evaluation.md](61_AI_Evaluation.md). |
| Provider Credentials | Never stored as plain configuration — provider API keys are Secrets, per [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s Security Domain-owned `GetSecret` port; this setting *references* a stored credential, it does not hold credential material directly. |

## Prompt Templates vs. System Instructions: A Guardrail Boundary

The distinction drawn above between administrator-configurable Prompt Templates (Enterprise Rules) and platform-controlled System Instructions is a deliberate governance boundary, not an oversight: allowing an organization to override System Instructions would allow a misconfigured or malicious administrator to disable the AI Design Philosophy's binding rules (e.g., removing the hallucination-prevention instruction) for their own workspace, undermining the AI Guardrails architecture ([63_AI_Guardrails.md](63_AI_Guardrails.md)). Enterprise Rules may *add* organization-specific constraints (e.g., "always flag PII in responses") but may never *remove* a System Instruction-level guarantee.

## Versioning and Auditability

**Binding rule:** AI Configuration SHALL be versioned and auditable.

- **Versioned:** Every AI Configuration setting follows the Versioning Model from [44_Global_Entity_Model.md](44_Global_Entity_Model.md) — a change to Default Model, Confidence Threshold, or any other setting creates a new version, with the prior version retained and retrievable, never overwritten in place. This is what makes [61_AI_Evaluation.md](61_AI_Evaluation.md)'s automated benchmarking meaningful across configuration changes — a regression can be attributed to a specific configuration version.
- **Auditable:** Every AI Configuration change SHALL produce an Audit Event, per the "Configuration Change" auditable action already established in [47_Data_Governance.md](47_Data_Governance.md), with the specific setting, prior value, new value, and changing actor recorded.

## Responsibilities

- Every new AI Subsystem Layer capability that introduces a tunable parameter must be added to the Configurable AI Settings table and routed through the same versioned, audited Configuration Domain mechanism — no AI setting may be configured via an untracked environment variable or hard-coded constant once it is intended to be administrator-configurable.
- The System Instructions/Enterprise Rules boundary is a security-relevant architectural decision; any later-phase proposal to make System Instructions organization-overridable requires an ADR with explicit AI Guardrails review, not a routine configuration-surface expansion.

## Constraints

- This document does not specify default values for any setting (e.g., a default Confidence Threshold) — Deferred to Architecture.
- This document does not specify the administrative UI/UX for configuring these settings — a Frontend Layer concern outside this specification's scope.

## Future Considerations

- As multi-provider usage matures, Provider Credentials management may warrant per-provider granular scoping (e.g., a workspace permitted to use OpenAI but not a self-hosted Local Model for compliance reasons) — an extension of this document's configuration model, not a redesign.

## Acceptance Criteria

- [ ] All thirteen configurable AI settings from the governing specification are defined with what they govern.
- [ ] Provider Credentials are explicitly connected to Secrets management, not treated as plain configuration.
- [ ] The System Instructions/Prompt Templates governance boundary is explained with its security rationale, not merely asserted.
- [ ] Versioning and auditability are both stated as binding requirements with their enforcement mechanism.
