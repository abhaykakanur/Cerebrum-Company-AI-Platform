# Repository Architecture

## Monorepo Rationale

Cerebrum is a single monorepo (not separate repositories per app) because
the Modular Monolith's backend and its frontend evolve together against
one shared API contract and one shared CES specification — see
`docs/architecture/specification/30_System_Architecture.md`'s Modular
Monolith Decision Rationale, which this repository structure directly
extends to the source-control level.

## Two Package Managers, One Monorepo

| Ecosystem | Tool | Scope |
|---|---|---|
| Python | uv workspace | `apps/backend/` |
| TypeScript | pnpm workspace | `apps/frontend/`, `packages/*` |

These are independent workspaces coordinated by convention (both rooted
at the repository root, both invoked via `scripts/*.sh`), not merged into
a single tool — Python and TypeScript have fundamentally different
dependency resolution models, and forcing them into one tool would add
complexity without benefit.

## Top-Level Layout

```
apps/           Deployable applications (backend, frontend)
packages/        Shared TypeScript libraries consumed by apps/ and each other
infrastructure/   Local infrastructure provisioning (Docker Compose)
docs/              All documentation, including the CES specification
scripts/            Developer commands — the primary interface to this repo
config/              Per-environment configuration
tests/                Cross-cutting, full-stack tests (not app-scoped)
tools/                 Reserved for future custom developer tooling
examples/               Reserved for future usage examples
assets/                  Reserved for shared static assets (e.g., brand assets)
```

See `docs/architecture/folder-structure.md` for the complete, per-directory
breakdown.

## Why `apps/` and Not Flat Top-Level `backend/`/`frontend/`

Grouping deployable applications under `apps/` (with shared libraries
under `packages/`) is a standard, well-understood monorepo convention that
scales cleanly if a third deployable (e.g., a future CLI or worker-only
process) is added later — it would join `apps/` without restructuring
anything else.

## Relationship to the CES

`docs/architecture/specification/` contains the complete, 108-document
Cerebrum Engineering Specification — the authoritative source of truth
this repository implements. This document and its siblings in
`docs/architecture/` are the **repository-specific** operationalization of
that specification (how the code is actually organized on disk); they do
not redefine anything the CES already decided. Where this document and the
CES ever appear to disagree, the CES governs — see `CONTRIBUTING.md`.
