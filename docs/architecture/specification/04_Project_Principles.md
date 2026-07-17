# 04 — Project Principles

## Purpose

This document establishes the non-negotiable engineering, product, and AI principles that govern all future Cerebrum work. Principles here are constraints, not preferences — later phases must comply with them rather than trade them off for convenience.

## Scope

This document covers product principles, engineering philosophy, and AI philosophy as durable constraints. It does not cover specific goals ([02_Project_Goals.md](02_Project_Goals.md)) or metrics ([08_Success_Metrics.md](08_Success_Metrics.md)).

## Definitions

- **Principle** — A constraint on design and implementation that holds regardless of feature, phase, or team, unless formally superseded through governance.
- **Least Privilege** — The practice of granting the minimum access necessary for a given operation, and no more.

## Product Principles

1. **Single Source of Truth** — Enterprise data, not the AI model, is authoritative. Every subsystem must be designed to preserve and expose provenance back to source systems.
2. **Security by Default** — Systems must default to the most restrictive safe configuration; access must be explicitly granted, never implicitly assumed.
3. **Explainability** — Every AI-derived answer must be traceable to the data and reasoning that produced it.
4. **Human Oversight** — Automated processes that affect knowledge structure, access, or AI answers must remain reviewable and correctable by humans.
5. **Modularity** — Components must be independently replaceable without requiring a redesign of the whole system.
6. **Scalability** — Design decisions must remain valid at enterprise scale (thousands of organizations, millions of documents), not only at prototype scale.
7. **Extensibility** — New source systems, content types, and capabilities must be addable without architectural rework.
8. **Observability** — System behavior, including AI reasoning and retrieval, must be inspectable, loggable, and auditable.
9. **Fault Tolerance** — Failure in one connector, subsystem, or dependency must not silently corrupt or block unrelated functionality.
10. **Least Privilege** — Every actor — human, service, or AI component — operates with the minimum access required for its function.

## Engineering Philosophy

- **Architecture first.** Design decisions precede implementation; implementation does not retroactively define architecture.
- **Documentation first.** Specification and design documentation precede code.
- **Code second.** Code is the expression of an already-agreed design, not the vehicle for discovering it.
- **Quality over quantity.** Fewer, correct capabilities are preferred over many partially-working ones.
- **Correctness over cleverness.** Straightforward, verifiable solutions are preferred over clever ones that are harder to verify.
- **Maintainability over shortcuts.** Long-term maintainability takes precedence over short-term implementation speed.
- **Explicit over implicit.** Behavior, configuration, and contracts must be stated explicitly, not inferred from convention alone.
- **Simple architecture over unnecessary complexity.** Complexity must be justified by a real requirement, not introduced speculatively.
- **Enterprise standards over tutorial standards.** All work is held to production, multi-tenant, enterprise-grade standards — not to the standards of a demo or proof of concept.

## AI Philosophy

Restated from [01_Product_Vision.md](01_Product_Vision.md) as binding principles, not aspirational statements:

- The AI is a reasoning engine, not a source of truth.
- Enterprise data is the source of truth.
- Answers must be grounded whenever grounding is possible.
- Factual answers must attempt citation.
- Confidence must be exposed, not hidden.
- Hallucination minimization is a required design goal, not a nice-to-have.
- An unknown answer is preferable to a fabricated one.

## Responsibilities

- Every architecture and design document produced in later phases must state, where relevant, which principles it upholds and how.
- A design that appears to violate a principle listed here must either be revised or must raise an ADR justifying the exception, per [09_Governance.md](09_Governance.md).
- Reviewers of future technical designs should treat this document as a checklist, not merely as background reading.

## Constraints

- Principles in this document may not be silently dropped by an implementation phase. They may only be superseded through the governance process.
- Where two principles are in tension for a specific design (for example, Observability and Least Privilege, or Scalability and Simplicity), the tension must be resolved explicitly in the relevant design document, not left implicit.

## Future Considerations

- As real-world implementation surfaces tradeoffs between principles, this document should accumulate a log of resolved tensions (e.g., via linked ADRs) rather than being edited to remove the tension.
- Additional principles may be proposed in later phases (e.g., a specific data residency principle) but must go through governance review before being added here.

## Acceptance Criteria

- [ ] All ten product principles are listed, unaltered in substance from the governing specification.
- [ ] Engineering philosophy and AI philosophy are both present as binding statements, not marketing language.
- [ ] The document defines a clear process for handling principle conflicts (via governance), rather than leaving conflicts unaddressed.
