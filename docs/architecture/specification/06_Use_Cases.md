# 06 — Use Cases

## Purpose

This document enumerates the primary use cases Cerebrum must support. It connects the target user roles in [05_Target_Users.md](05_Target_Users.md) to concrete workflows, giving later architecture phases a grounded basis for functional requirements.

## Scope

This document covers the primary use cases named in the governing specification. It does not define interaction design, API surfaces, or data models — those are later-phase concerns. Each use case is described at the level of user intent, not implementation.

## Definitions

- **Use Case** — A recurring user intent that Cerebrum must be able to satisfy, independent of the specific interface used to express it.
- **Institutional Knowledge** — Knowledge that exists primarily in the experience of employees rather than in a formally maintained document.

## Primary Use Cases

1. **Find company knowledge** — Locate relevant organizational information without knowing in advance which system holds it.
2. **Search documentation** — Query formal documentation across all connected knowledge sources.
3. **Search code** — Query source code and related technical artifacts.
4. **Search tickets** — Query issue trackers and support/engineering ticketing systems.
5. **Search architecture decisions** — Locate past architectural decisions and their rationale.
6. **Search meeting summaries** — Locate discussion outcomes and decisions made in meetings.
7. **Locate experts** — Identify which person or team holds relevant knowledge on a given topic.
8. **Understand historical decisions** — Retrieve not just what was decided, but why.
9. **Understand project evolution** — Trace how a project, system, or initiative changed over time.
10. **Find dependencies** — Identify relationships and dependencies between systems, teams, or projects.
11. **Generate knowledge summaries** — Produce synthesized overviews of a topic drawn from multiple sources.
12. **Visualize relationships** — Present connections between knowledge entities in a comprehensible visual form.
13. **Understand organizational history** — Reconstruct how the organization arrived at its current state.
14. **Retrieve institutional knowledge** — Surface knowledge that would otherwise depend on a specific employee's memory.
15. **Support employee onboarding** — Give new employees a reliable path to organizational context.
16. **Support incident investigations** — Provide relevant historical and technical context during an incident.
17. **Support architecture reviews** — Surface prior decisions, patterns, and constraints relevant to a proposed design.
18. **Support compliance audits** — Provide traceable, citation-backed evidence for audit purposes.
19. **Support technical discovery** — Help engineers understand unfamiliar systems before making changes.
20. **Support enterprise research** — Support open-ended research questions that span multiple knowledge sources.

## Responsibilities

- Each use case listed here must map to at least one target user role in [05_Target_Users.md](05_Target_Users.md) and at least one core responsibility in [03_Product_Definition.md](03_Product_Definition.md).
- Later architecture phases must ensure that functional requirements trace back to this list; features with no traceable use case should be questioned before being built.
- Use cases involving compliance, audits, or incident investigation carry a heightened need for explainability and citation, per the AI Philosophy in [04_Project_Principles.md](04_Project_Principles.md).

## Constraints

- This document intentionally avoids prescribing UI flows, query syntax, or output formats.
- Use cases are listed in the order given by the governing specification, not in priority order. Relative prioritization is a planning-phase decision.

## Future Considerations

- As Cerebrum's connector coverage expands, new use cases may emerge (e.g., use cases tied to video/meeting recording analysis at greater depth). New use cases should be added here only through governance review, and must still map to an existing core responsibility.
- Use cases that imply write-back to source systems (e.g., "resolve this ticket") are explicitly not covered by this list and would require a non-goal reassessment per [07_Non_Goals.md](07_Non_Goals.md) before being considered.

## Acceptance Criteria

- [ ] All twenty primary use cases from the governing specification are listed.
- [ ] Each use case is stated as a user intent, not an implementation detail.
- [ ] No use case implies functionality excluded by [07_Non_Goals.md](07_Non_Goals.md).
