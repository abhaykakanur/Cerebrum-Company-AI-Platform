# 99 — Coding Standards

## Purpose

This document defines Cerebrum's coding standards: the nine general rules governing code across all languages, and the specific Code Quality tooling enforcing them. It elaborates [32_Technology_Stack.md](32_Technology_Stack.md)'s language choices (Python, TypeScript, SQL, Cypher) with concrete, enforceable standards.

## Scope

This document covers coding-style and quality standards. It does not contain code examples or language-specific syntax guidance beyond naming the governing tools — Deferred to Architecture-time style guides.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Languages

Per [32_Technology_Stack.md](32_Technology_Stack.md): Python, TypeScript, SQL, Cypher. This document's General Rules apply across all four, adapted to each language's idioms; the Code Quality tooling below is language-specific.

## General Rules

| Rule | Meaning |
|---|---|
| Meaningful names | Identifiers describe what they represent, not their type or an abbreviation requiring lookup — directly implementing Explicit over Implicit ([04_Project_Principles.md](04_Project_Principles.md)). |
| No magic numbers | A literal value with unclear meaning is named as a constant, not embedded inline — supporting Readable and Self-Documenting from [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s Engineering Principles. |
| Small functions | A function does one thing, per Single Responsibility ([34_Architecture_Principles.md](34_Architecture_Principles.md)) applied at the function level, not only the class/module level. |
| Single responsibility | Restated at the class/module level per [34_Architecture_Principles.md](34_Architecture_Principles.md). |
| Dependency injection | Per [34_Architecture_Principles.md](34_Architecture_Principles.md)'s Dependency Injection principle — no direct instantiation of an Infrastructure Layer adapter inside Domain or Application Layer code. |
| Avoid global state | No mutable module-level or process-global state that could be mutated from multiple call paths unpredictably — supports both Testability (Unit Tests requiring isolation, [98_Testing_Strategy.md](98_Testing_Strategy.md)) and correctness under the Horizontal Scaling model ([39_Performance_Targets.md](39_Performance_Targets.md)), where global state on one instance would not be visible to another. |
| Composition over inheritance | Per [34_Architecture_Principles.md](34_Architecture_Principles.md). |
| Strong typing | Per the Strongly Typed Engineering Principle ([95_DevOps_Architecture.md](95_DevOps_Architecture.md)) — see Decision Rationale below. |
| Explicit error handling | Every error is classified per [38_Observability.md](38_Observability.md)'s error taxonomy at the point it is raised or caught — no bare, unclassified exception handling that silently swallows an error's category information. |

### Decision Rationale: Why Strict Typing

Strong, strict typing (Pydantic and type hints in Python, TypeScript Strict Mode in the frontend) is mandated because it directly supports three binding requirements elsewhere in this specification: (1) the Application Layer's DTO Validation ([34_Architecture_Principles.md](34_Architecture_Principles.md)) depends on types being enforced, not merely documented, to catch malformed data at the boundary rather than deep inside domain logic; (2) Explicit over Implicit ([04_Project_Principles.md](04_Project_Principles.md)) — a strongly typed function signature is itself a form of self-documentation that cannot silently drift out of sync with behavior the way a comment can; (3) refactoring safety at the scale of 30 domains and 200 requirements ([20_Functional_Requirements.md](20_Functional_Requirements.md)) — a change to a shared type (e.g., the Base Entity Envelope, [44_Global_Entity_Model.md](44_Global_Entity_Model.md)) is caught at compile/type-check time across every consumer, rather than surfacing as a runtime failure discovered only in production or, worse, silently producing incorrect behavior.

## Code Quality Tooling

Enforce: Black (Python), Ruff, isort, mypy, ESLint, Prettier, TypeScript Strict Mode.

| Tool | Language | Purpose |
|---|---|---|
| Black | Python | Automated, non-configurable code formatting — eliminates formatting debate entirely. |
| Ruff | Python | Fast linting, covering style and common-bug-pattern rules. |
| isort | Python | Import statement ordering and grouping, consistent with [33_Directory_Structure.md](33_Directory_Structure.md)'s package structure. |
| mypy | Python | Static type checking, enforcing the Strong Typing rule above. |
| ESLint | TypeScript | Linting, style and correctness rules for the Frontend Layer. |
| Prettier | TypeScript | Automated code formatting, the frontend's Black equivalent. |
| TypeScript Strict Mode | TypeScript | The compiler's strictest type-checking configuration, enabled platform-wide, no exceptions. |

**Binding rule:** No lint warnings allowed in production. A lint warning is treated with the same severity as a lint error for merge purposes — there is no "warning, but acceptable" tier that accumulates silently over time, directly preventing the "quick fixes become permanent architecture" failure mode named in [95_DevOps_Architecture.md](95_DevOps_Architecture.md) from manifesting as accumulated lint debt.

## Responsibilities

- Every one of these tools runs as a blocking CI/CD pipeline stage ([97_CICD_Architecture.md](97_CICD_Architecture.md), stages 2–4) — no exceptions are merged around these checks without an explicit, reviewed, and time-bound suppression (Deferred to Architecture for the suppression mechanism itself, which must itself be auditable).
- Every General Rule violation identified in code review must be corrected before merge or explicitly justified as a deliberate exception with an ADR, per [09_Governance.md](09_Governance.md), never silently waived.

## Constraints

- This document does not specify exact tool configuration (line length, specific rule sets enabled/disabled) — Deferred to Architecture-time configuration files.
- This document does not cover SQL or Cypher-specific linting tooling — Deferred to Architecture, since the ecosystem tooling for these query languages is less standardized than for Python/TypeScript.

## Future Considerations

- As SQL and Cypher usage grows in volume, dedicated linting/formatting tooling for these languages should be evaluated and added to this document's Code Quality Tooling table, closing the current gap relative to Python/TypeScript's mature tooling coverage.

## Acceptance Criteria

- [ ] All four languages from [32_Technology_Stack.md](32_Technology_Stack.md) are acknowledged as in scope.
- [ ] All nine General Rules from the governing specification are defined with their connection to existing architectural principles.
- [ ] The Strict Typing Decision Rationale is included.
- [ ] All seven Code Quality tools from the governing specification are listed with purpose, and the "no lint warnings in production" rule is stated as binding.
