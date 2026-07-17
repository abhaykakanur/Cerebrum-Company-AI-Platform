# Dependency Rules

These rules are **binding and enforced in code review** — not style
guidance. They are the concrete, repository-level expression of
`docs/architecture/specification/34_Architecture_Principles.md`'s
Dependency Inversion principle and
`docs/architecture/specification/30_System_Architecture.md`'s
Non-Negotiable Extraction Seam constraint.

## The Core Rule

```
domain/
   ↑
application/
   ↑
infrastructure/
```

Dependencies point inward, always:

- `infrastructure/` may import from `application/` and `domain/`.
- `application/` may import from `domain/` only.
- `domain/` imports from neither `application/` nor `infrastructure/` —
  it depends on nothing else in the backend.

**No reverse dependency.** A domain-layer module importing from
`infrastructure/` (even "just this once, for convenience") is a
review-blocking finding, not a style nitpick.

**No circular dependency.** If domain A needs something from domain B and
domain B needs something from domain A, at least one of those
relationships must be re-modeled — typically via a domain event (see
`apps/backend/src/cerebrum/events/`) rather than a direct call, exactly
as `docs/architecture/specification/35_Domain_Architecture.md`'s
Dependency Graph Verification resolved three such cases during CES
authoring. See that document's "Dependency Graph Verification" section
for the worked examples.

**No feature coupling.** A domain's `domain/` and `application/` code
never imports another domain's `infrastructure/` or internal `domain/`
submodules directly — only another domain's published `application/`
service interface, once domain subpackages exist. This is what preserves
the extraction seam: any domain could become an independent service later
by swapping its infrastructure adapters, without its consumers noticing.

## Cross-Cutting Layers

`core/`, `config/`, `middleware/`, `dependencies/`, `api/` sit outside the
domain/application/infrastructure triad and may be imported more broadly
(e.g., every layer may import shared base types from `core/`) — but they
still never import "downward" into a specific domain's internals.

## Frontend Rule

`apps/frontend/` never imports from `apps/backend/` directly, and vice
versa — they communicate exclusively over HTTP through the API layer
(`apps/backend/src/cerebrum/api/`), consumed via `apps/frontend/lib/`'s
API client. This is enforced by their being separate deployable processes,
not merely by convention.

## Enforcement

At this milestone, these rules are enforced by code review only — an
automated import-linter (Deferred to Architecture; see
`docs/architecture/specification/33_Directory_Structure.md`'s
"Dependency Flow Enforcement" for the general requirement) is expected to
be added once enough domain code exists to make automation worthwhile.
Until then, every reviewer is responsible for checking this document's
rules on every pull request.
