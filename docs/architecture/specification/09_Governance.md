# 09 — Governance

## Purpose

This document defines how decisions about Cerebrum's architecture and specification are made, recorded, and changed over time. It exists to ensure that the authority established in [00_Project_Charter.md](00_Project_Charter.md) is exercised consistently as the project moves through future phases.

## Scope

This document covers versioning rules, architectural decision-making process, and the relationship between specification and implementation across phases. It does not cover team structure, staffing, or day-to-day project management, which are out of scope for Phase 0.

## Definitions

- **Architecture Decision Record (ADR)** — A documented record of a significant architectural or specification decision, including the context, the decision, and its consequences.
- **Breaking Change** — A change to a specification, API, or schema that invalidates previously valid assumptions made by dependent work.
- **Architectural Review** — The process by which a proposed decision or change is evaluated against this specification before being accepted.

## Versioning

- Every architectural decision shall be versioned.
- Every specification document shall be versioned.
- Every API shall be versioned, once APIs exist in later phases.
- Every schema shall be versioned, once schemas exist in later phases.
- This document set is versioned as CES (Cerebrum Engineering Specification) 1.0, Phase 0, Part 1, as stated in the document header of the governing specification.

## Architectural Governance

- **The architecture is authoritative.** Once established, architecture governs implementation choices.
- **Implementation follows architecture.** Engineers implement what the architecture specifies.
- **Implementation never redefines architecture.** A discovery made during implementation that suggests the architecture should change must be routed back through architectural review — it must not simply be coded around.
- **Every major decision shall receive an ADR.** "Major" includes any decision that: selects a core technology, alters a principle's application, changes a schema in a breaking way, or narrows/broadens a goal, use case, or non-goal.
- **Every future phase shall reference this specification.** Phase-specific documents must cite the Phase 0 documents they build upon rather than restating or silently reinterpreting them.

## Change Process

1. A proposed change to any Phase 0 document, or a significant architectural decision in a later phase, is written up as an ADR stating: context, options considered, the decision, and consequences.
2. The ADR undergoes architectural review against this specification, in particular against [04_Project_Principles.md](04_Project_Principles.md) and [07_Non_Goals.md](07_Non_Goals.md).
3. If accepted, the ADR is recorded and the affected document(s) are updated with a version increment and a reference to the ADR.
4. Breaking changes require explicit architectural review before merge; they may not be introduced incidentally as part of an unrelated change.

## Responsibilities

- Anyone proposing a change to this specification is responsible for writing the ADR, not merely implementing the change and describing it after the fact.
- Reviewers are responsible for checking proposed changes against the full Phase 0 document set for consistency, not just against the single document being changed.
- This document itself is subject to the same governance process it describes; changes to governance require an ADR.

## Constraints

- No ADR template, tooling, or storage location is prescribed in this phase. That is a process-tooling decision for a later phase.
- This document does not define organizational roles empowered to approve ADRs (e.g., a named architecture review board). That is intentionally left as an open question — see [11_Open_Questions.md](11_Open_Questions.md).

## Future Considerations

- A formal ADR template and repository location should be established before Phase 1 architecture work begins.
- A named decision-making body (e.g., an architecture review board) should be established once the project has assigned stakeholders.

## Acceptance Criteria

- [ ] Versioning requirements are stated for decisions, specifications, APIs, and schemas.
- [ ] The relationship between architecture and implementation is stated unambiguously ("architecture is authoritative").
- [ ] A concrete, if lightweight, change process is defined (propose → review → record).
- [ ] Open questions about governance tooling and authority are deferred explicitly to [11_Open_Questions.md](11_Open_Questions.md) rather than silently assumed.
