# 109 — Project Governance

## Purpose

This document defines the eight elements of ongoing project governance carrying this specification's discipline into implementation, plus the Technical Debt Policy. It elaborates and operationalizes [09_Governance.md](09_Governance.md) (Part 1) for the implementation phase specifically.

## Scope

This document covers governance roles, processes, and the technical debt policy. It does not redefine the ADR process itself (see [09_Governance.md](09_Governance.md)) or Code Review mechanics (see [97_CICD_Architecture.md](97_CICD_Architecture.md)), which this document references rather than restates.

## Definitions

See [10_Glossary.md](10_Glossary.md) and [09_Governance.md](09_Governance.md). No new terms are introduced here beyond Technical Debt Policy's own vocabulary below.

## Governance Elements

| Element | Definition |
|---|---|
| Architecture Owner | The individual or body with final authority to approve/reject ADRs and resolve conflicts between this specification and a proposed implementation deviation — the role [09_Governance.md](09_Governance.md) left as Open Question 1 in [27_Open_Questions.md](27_Open_Questions.md), still requiring a named assignment before implementation begins. |
| Code Review Rules | Per [97_CICD_Architecture.md](97_CICD_Architecture.md)'s Code Review section — every PR requires Description, Linked Requirement, Linked ADR (if applicable), Testing Evidence, Screenshots (UI), Review Checklist, Approval. |
| Branch Protection | Per [97_CICD_Architecture.md](97_CICD_Architecture.md)'s Version Control section — `main` and `develop` require passing CI/CD ([97_CICD_Architecture.md](97_CICD_Architecture.md)'s thirteen stages) and at least one Approval before merge; exact required-approval counts are Open Question 121. |
| Release Approval | A defined sign-off gate before a release reaches Production, distinct from the per-PR Approval — corresponds to [97_CICD_Architecture.md](97_CICD_Architecture.md)'s Deployment Approval pipeline stage, with the specific approver role Deferred to Architecture per Open Question 118 in [104_Open_Questions.md](104_Open_Questions.md). |
| Documentation Standards | Per [100_Documentation_Standards.md](100_Documentation_Standards.md) — every module ships with its seven-section README before being considered complete. |
| Change Management | The ADR process per [09_Governance.md](09_Governance.md): propose → architectural review → record → version increment. This is the single change-management mechanism for both specification changes (as demonstrated by this CES's own Open Questions resolution process) and significant implementation-time architectural decisions. |
| Versioning Policy | Per [09_Governance.md](09_Governance.md) (specification/decision versioning) and [80_API_Architecture.md](80_API_Architecture.md) (API Major/Minor versioning) and [66_Connector_SDK.md](66_Connector_SDK.md) (Connector Version) — three distinct, already-specified versioning schemes, each scoped to what it versions, restated here as the unified governance expectation that every versionable artifact in Cerebrum has exactly one of these three schemes applied to it, never an ad hoc fourth. |
| Security Review | Per [79_Threat_Model.md](79_Threat_Model.md) and [98_Testing_Strategy.md](98_Testing_Strategy.md)'s Security Testing — every release undergoes the Security Scanning CI/CD stage ([97_CICD_Architecture.md](97_CICD_Architecture.md)), with a deeper, periodic manual security review recommended at each Milestone ([111_Project_Milestones.md](111_Project_Milestones.md)), particularly given the AI-specific security priorities flagged in [64_Open_Questions.md](64_Open_Questions.md) (prompt injection, PII, secret detection). |

## Technical Debt Policy

Every technical debt item SHALL include: Description, Reason, Impact, Owner, Priority, Removal Plan, Deadline.

| Field | Purpose |
|---|---|
| Description | What the debt is — a specific, identifiable shortcut or gap, not a vague "needs cleanup." |
| Reason | Why it was taken — typically a deadline or complexity tradeoff, honestly stated. |
| Impact | What it costs the system while it persists (performance, maintainability, security exposure). |
| Owner | Who is accountable for eventually resolving it. |
| Priority | Its relative urgency among other tracked debt. |
| Removal Plan | The specific steps that will resolve it — not merely "will fix later" without a plan. |
| Deadline | When it must be resolved by, converting an open-ended intention into a tracked commitment. |

**Binding rule:** No undocumented technical debt. This directly enforces [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s "no quick fixes become permanent architecture" principle with a concrete tracking mechanism — a shortcut is legitimate only if it is immediately entered into this tracked register with all seven fields, making its existence visible and its resolution accountable, rather than existing only in the memory of the engineer who introduced it.

**Current technical debt status:** As of this specification's completion, zero technical debt items exist, since Phase 0 has produced documentation only — no source code has been written per this CES's binding "do not write code" constraint across every part. This policy is the mechanism by which debt will be tracked from the first line of Phase 1 code onward, not a record of debt already incurred.

## Responsibilities

- The Architecture Owner role must be named before Phase 1 (Project Foundation, [110_Implementation_Roadmap.md](110_Implementation_Roadmap.md)) begins — this is a prerequisite, not a parallel-track item, since ADR approval authority is needed from the first implementation decision onward.
- Every technical debt item logged during implementation must be reviewed at least once per Milestone ([111_Project_Milestones.md](111_Project_Milestones.md)) to confirm its Deadline remains realistic or trigger explicit re-prioritization, never silent deadline slippage.

## Constraints

- This document does not name a specific individual as Architecture Owner — that is an organizational staffing decision outside this specification's scope, per [00_Project_Charter.md](00_Project_Charter.md)'s original deferral of RACI/staffing to a dedicated planning phase.
- This document does not specify a technical-debt-tracking tool — Deferred to Architecture/operations.

## Future Considerations

- As the engineering organization grows, Release Approval and Security Review roles may need to be formally separated from the Architecture Owner role to avoid a single-point-of-approval bottleneck — a natural organizational evolution, not a defect in the current single-owner model appropriate for Cerebrum's current scale.

## Acceptance Criteria

- [ ] All eight Governance Elements from the governing specification are defined, each connected to its existing CES mechanism rather than introducing a new, disconnected process.
- [ ] The Technical Debt Policy's seven required fields are defined, with the "no undocumented technical debt" rule stated as binding.
- [ ] Current technical debt status is honestly stated as zero, with the reason (documentation-only phase) explicit.
