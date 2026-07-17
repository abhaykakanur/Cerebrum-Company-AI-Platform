# 11 — Open Questions

## Purpose

This document records requirements and decisions that are ambiguous in the current specification. Per project instruction, ambiguity must be recorded here rather than resolved by assumption. Every question in this document must be explicitly answered — via governance review and an ADR — before the phase of work it blocks may proceed.

## Scope

This document covers ambiguities identified during the production of the Phase 0 document set. It will be revised as questions are resolved (moved to a "Resolved" section with a link to the governing ADR) and as new ambiguities surface in later phases.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced in this document.

## Open Questions

| # | Question | Why It Is Open | Blocks |
|---|---|---|---|
| 1 | Who holds authority to approve an ADR (a named architecture review board, a single architect, or a rotating body)? | [09_Governance.md](09_Governance.md) defines the change process but not the approving authority. | Any future governance action. |
| 2 | Does Cerebrum implement its own role-based permission model, or does it purely inherit and mirror access boundaries from connected source systems? | [05_Target_Users.md](05_Target_Users.md) lists roles but does not resolve how role maps to access; [04_Project_Principles.md](04_Project_Principles.md) mandates Security by Default and Least Privilege without specifying the mechanism. | Permission architecture, connector design. |
| 3 | Is Cerebrum a single-tenant-per-deployment system, a multi-tenant SaaS system, or does it support both? | The mission statement targets "thousands of organizations," implying multi-tenancy, but no explicit tenancy model is stated. | Data isolation architecture, infrastructure design. |
| 4 | Does Cerebrum ever write back to source systems, or is it strictly read-only against connected systems? | [07_Non_Goals.md](07_Non_Goals.md) establishes augmentation over replacement but does not explicitly rule out limited write-back (e.g., writing a summary back into a wiki). | Connector architecture, security scope. |
| 5 | What is the data retention and deletion policy, especially where "preserve knowledge" (a core responsibility) may conflict with source-system deletion, legal holds, or data-subject deletion requests (e.g., GDPR "right to be forgotten")? | [01_Product_Vision.md](01_Product_Vision.md) and [03_Product_Definition.md](03_Product_Definition.md) mandate preservation and versioning without addressing deletion obligations. | Data architecture, compliance posture. |
| 6 | How is "confidence" concretely measured and exposed to users — a numeric score, a qualitative label, or a citation-density proxy? | The AI Philosophy in [01_Product_Vision.md](01_Product_Vision.md) and [04_Project_Principles.md](04_Project_Principles.md) requires confidence exposure without defining its representation. | AI/reasoning architecture, UX design. |
| 7 | What is the resolution process when source systems contain conflicting information (e.g., an outdated wiki page contradicts a recent decision record)? | The Single Source of Truth principle assumes enterprise data is authoritative, but does not address internally inconsistent enterprise data. | Knowledge structuring and ranking design. |
| 8 | What is the required index freshness (real-time, near-real-time, or scheduled batch) per source-system type? | [08_Success_Metrics.md](08_Success_Metrics.md) names "index freshness" as a metric category without a target or refresh strategy. | Ingestion architecture. |
| 9 | Does the "thousands of organizations and millions of enterprise documents" scale target apply per-tenant, in aggregate across all tenants, or both? | Stated in the governing specification's framing instructions without a precise unit of measure. | Capacity planning, infrastructure architecture. |
| 10 | What is the AI model sourcing strategy — a single model provider, multiple providers, and/or self-hosted models — and does it vary by deployment (cloud vs. on-premise)? | The AI Philosophy defines behavioral requirements (grounding, confidence, hallucination minimization) but not sourcing. | AI architecture, vendor strategy. |
| 11 | What compliance certifications or regulatory regimes (e.g., SOC 2, ISO 27001, HIPAA, GDPR, industry-specific regulation) is Cerebrum required to support, and does this vary by customer segment? | Not addressed in Phase 0; implied by "enterprise-grade" and Legal/Compliance use cases in [06_Use_Cases.md](06_Use_Cases.md). | Security architecture, go-to-market scope. |
| 12 | For video and audio content (e.g., meeting recordings), what is the required depth of understanding — transcription and keyword search only, or deeper semantic/speaker-aware understanding? | Listed as a knowledge source in [01_Product_Vision.md](01_Product_Vision.md) without a defined processing depth. | Ingestion and extraction architecture. |
| 13 | Who owns derived/extracted knowledge artifacts (e.g., an AI-generated summary of a customer's proprietary document) from an intellectual-property and data-handling perspective? | Not addressed in Phase 0. | Legal terms, data architecture. |
| 14 | When an employee is offboarded, how quickly and completely must their access-derived visibility into Cerebrum be revoked, including previously generated answers or cached results? | Implied by Security by Default and permission correctness but not specified. | Permission architecture, session/cache design. |
| 15 | For the "locate experts" use case, what signal(s) determine that a person is an "expert" on a topic (e.g., authorship frequency, explicit tagging, organizational role)? | [06_Use_Cases.md](06_Use_Cases.md) names the use case without defining the underlying signal. | Relationship-mapping architecture. |
| 16 | What is the mechanism for the "continuously improve knowledge quality" responsibility — human-in-the-loop correction, automated staleness detection, both? | Named as a core responsibility in [03_Product_Definition.md](03_Product_Definition.md) without a defined mechanism. | Feedback-loop architecture. |
| 17 | Where is the precise boundary between permitted "augmentation" and prohibited "replacement" for borderline features (e.g., allowing comments on a surfaced document, or triggering a workflow in a connected system)? | [07_Non_Goals.md](07_Non_Goals.md) states a governing principle but not a bright-line test. | Feature scoping in all future phases. |

## Responsibilities

- No later-phase document may silently resolve one of these questions through implementation choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), and this document updated to reflect the resolution.
- Anyone identifying a new ambiguity during later-phase work is responsible for adding it here rather than proceeding on an undocumented assumption.

## Constraints

- This list is not exhaustive of every possible future ambiguity — it reflects what is identifiable from the Phase 0 document set as currently written.
- Questions here should not be answered within this document. This document's role is to record, not resolve.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added) with a link to the governing ADR and a one-line summary of the resolution, preserving history rather than deleting the record.
- Architecture-phase kickoff should treat unresolved questions that block that phase's work as hard prerequisites, not parallelizable work.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question states what future work it blocks.
- [ ] No question duplicates a decision already made elsewhere in the Phase 0 document set.
