# Coding Guidelines

The principles behind the practical rules in
`docs/development/coding-standards.md`. This document explains *why*;
that one explains *what command to run*.

## Every Principle Traces to the CES

None of these guidelines are invented here — each is the code-level
application of a principle already established in
`docs/architecture/specification/04_Project_Principles.md` and
`docs/architecture/specification/34_Architecture_Principles.md`.

| Guideline | CES Origin |
|---|---|
| Explicit over implicit — no hidden control flow, no magic | `04_Project_Principles.md` |
| Correctness over cleverness | `04_Project_Principles.md` |
| Simple architecture over unnecessary complexity | `04_Project_Principles.md` |
| Dependency Injection everywhere | `34_Architecture_Principles.md` |
| Composition over inheritance | `34_Architecture_Principles.md` |
| Immutable domain models where possible | `34_Architecture_Principles.md` |
| Single Responsibility, Small Functions | `34_Architecture_Principles.md` (SOLID) |

## What "Correctness Over Cleverness" Means Here

A straightforward, slightly more verbose solution that every reviewer can
verify at a glance is preferred over a compact one that requires
re-deriving the author's reasoning. This matters more in this codebase
than most: the CES's AI Philosophy (grounding, citation, hallucination
minimization) depends on every step of the retrieval/reasoning pipeline
being independently auditable — code that is clever enough to obscure
what it does undermines that auditability at the implementation level,
not just at the architecture level.

## No Comments Explaining "What" — Only "Why"

Well-named identifiers explain what code does. A comment should only
exist for a non-obvious constraint, a workaround for a specific bug, or a
subtlety a reader would otherwise miss — not to restate what the next
line already says.

## No Premature Abstraction

Do not introduce an interface, a factory, or a configuration option for a
need that does not yet exist. Three similar lines of code are better than
a premature shared abstraction that guesses wrong about future
requirements — consistent with "Simple architecture over unnecessary
complexity."

## No Undocumented Shortcuts

If a shortcut is genuinely necessary, it is logged as tracked technical
debt (Description, Reason, Impact, Owner, Priority, Removal Plan,
Deadline) per `docs/architecture/specification/109_Project_Governance.md`
— never left silently in the code for someone else to discover later.

## Error Handling

Every error is classified into the taxonomy in
`docs/architecture/specification/38_Observability.md` (Validation,
Security, Connector, AI, Storage, Search / Recoverable vs. Fatal) at the
point it's raised — a bare `except Exception` or an unclassified
try/catch that discards the distinction is not acceptable, since
downstream error handling (retry logic, user messaging, alerting) depends
on that classification surviving.
