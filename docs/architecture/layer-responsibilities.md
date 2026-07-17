# Layer Responsibilities

The three architectural layers every backend domain follows (Clean /
Hexagonal Architecture — `docs/architecture/specification/34_Architecture_Principles.md`).
This document defines what belongs in each layer *in general*; see
`docs/architecture/folder-responsibilities.md` for the concrete top-level
folders realizing them today.

## Domain Layer

**Contains:** Entities, aggregates, value objects, domain services, domain
events, repository *port interfaces* (not implementations), business
rules/invariants.

**Never contains:** Any framework import, any database/network call, any
knowledge of HTTP, JSON, or how it will be persisted.

**Test approach:** Pure unit tests, no mocking needed for the domain
object itself (mocks are only needed for its collaborators, if any).

## Application Layer

**Contains:** Use cases (one per CES-traceable requirement), command
handlers (state-mutating), query handlers (read-only), DTOs, orchestration
logic that calls domain objects to fulfill a use case.

**Never contains:** Business rules (those belong in the domain layer this
layer orchestrates) or technology-specific code (that belongs in
infrastructure).

**Test approach:** Unit tests with domain-layer collaborators used
directly (they're pure) and infrastructure-layer ports replaced with test
doubles.

## Infrastructure Layer

**Contains:** Adapters implementing a domain- or application-layer port
against real technology — database drivers, LLM provider SDKs, secrets
backends, external HTTP clients.

**Never contains:** Business rules. An infrastructure adapter translates
between the port's domain-language contract and the underlying
technology's native API — it does not decide anything a domain object
should decide.

**Test approach:** Integration tests against real (typically
containerized) infrastructure — this is the one layer unit tests
deliberately do not cover, since its entire value is the real technology
integration.

## Dependency Direction

```
infrastructure/  →  application/  →  domain/
```

Always inward. See `docs/architecture/dependency-rules.md` for the
enforced, binding version of this rule.

## Cross-Cutting Layers

Not every backend folder is one of these three. `api/`, `middleware/`,
`dependencies/`, `core/`, `config/` are cross-cutting concerns that exist
alongside this triad, not inside it — see
`docs/architecture/folder-responsibilities.md` for what each contains.
