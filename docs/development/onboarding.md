# Developer Onboarding Guide

Start here if you're new to this repository. This document is the
"welcome, here's how to become productive" guide — for the mechanical
steps to get your environment running, see
[getting-started.md](getting-started.md); this document is about
orientation: what exists, what doesn't yet, and where to look for
anything else.

## Day One

1. Run through [getting-started.md](getting-started.md) — clone, set up,
   verify. Do not skip "Verify It Worked."
2. Read [`docs/architecture/overview.md`](../architecture/overview.md) —
   the Architecture Summary. Five minutes, gives you the map before you
   read any code.
3. Skim [`docs/architecture/specification/README.md`](../architecture/specification/README.md)
   — you don't need to read all 108+ CES documents now, but you need to
   know they exist and that this codebase implements them, not the other
   way around. When you're unsure _why_ something is built a certain
   way, the answer is almost always in one of these documents.
4. Read [`docs/architecture/dependency-rules.md`](../architecture/dependency-rules.md)
   and [`docs/architecture/coding-guidelines.md`](../architecture/coding-guidelines.md)
   — both are enforced in code review, not optional style guidance.

## What Actually Exists Right Now

The Phase 1 platform foundation (below) is complete, and every business
domain built on top of it is real and running, not scaffolding:

| Layer                                                                                                                                                 | Status                                                                                                                 |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Infrastructure clients (PostgreSQL, Redis, Neo4j, Qdrant, MinIO, OpenSearch)                                                                          | Connected, with retry and graceful degradation — see `docs/architecture/infrastructure/`.                              |
| Identity, Security & Multi-Tenancy                                                                                                                    | JWT auth, RBAC, API keys, sessions — see `docs/architecture/security/`.                                                |
| API Platform                                                                                                                                          | Pagination, filtering, sorting, response envelopes, versioning, rate limiting, OpenAPI — see `docs/architecture/api/`. |
| Production hardening                                                                                                                                  | Config validation, Docker image, CI pipeline — this document's own milestone.                                          |
| Business domains (documents/processing, knowledge graph, semantic search, retrieval/RAG, AI chat, connectors, workflows, Employee Knowledge Capsules) | Implemented — `apps/backend/src/cerebrum/application/`, 130+ API routes (`docs/api/README.md`).                        |
| Frontend                                                                                                                                              | Implemented against every domain above — `apps/frontend/README.md`.                                                    |

If you're looking for where "the product" lives — document ingestion,
search, AI chat, the Employee Knowledge Capsule UI — start at
`apps/frontend/app/(app)/` for the pages and `apps/backend/src/cerebrum/application/`
for the business logic they call.

## Codebase Tour

```
apps/backend/src/cerebrum/
├── api/            HTTP routing + response schemas. No business logic.
├── application/    Use cases (auth, knowledge, knowledge_graph, semantic, retrieval, ai, conversation, connectors, workflows, capsules).
├── config/         Typed, validated settings — one class per subsystem.
├── core/           Application Factory, lifecycle, logging, exceptions.
├── dependencies/   FastAPI DI providers.
├── domain/         Business entities. Empty — Phase 2+.
├── infrastructure/ Datastore clients, security primitives, ORM models.
├── middleware/     The request pipeline (see middleware/registry.py).
├── repositories/   Data-access contracts + PostgreSQL implementations.
└── shared/         Cross-cutting error taxonomy.
```

Full annotated tree: `docs/architecture/folder-structure.md`. Layer
responsibilities and what may import what:
`docs/architecture/layer-responsibilities.md` and
`docs/architecture/dependency-rules.md`.

## How to Find Your Way to a Specific Answer

| Question                                               | Where                                                                                                                                             |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Why does X work this way?"                            | The relevant CES document under `docs/architecture/specification/` — check the module's own docstring first, it usually cites the exact document. |
| "What can I import from where?"                        | `docs/architecture/dependency-rules.md`, `docs/architecture/import-rules.md`.                                                                     |
| "How do I add a new FastAPI dependency?"               | `docs/architecture/dependency-injection.md`, `docs/architecture/api/dependency-guide.md`.                                                         |
| "How does authentication/RBAC work?"                   | `docs/architecture/security/`.                                                                                                                    |
| "How do I add pagination/filtering to a new endpoint?" | `docs/architecture/api/`.                                                                                                                         |
| "How do I run this locally?"                           | `getting-started.md`.                                                                                                                             |
| "How do I deploy this?"                                | `docs/deployment/production-deployment.md`.                                                                                                       |
| "Something's broken, now what?"                        | `docs/deployment/troubleshooting.md`.                                                                                                             |
| "What test do I write for X?"                          | `docs/testing/README.md`.                                                                                                                         |
| "What's next on the roadmap?"                          | `docs/architecture/specification/110_Implementation_Roadmap.md`.                                                                                  |

## The CIS Prompt Model

This codebase is built phase-by-phase against numbered CIS
("Cerebrum Implementation Specification") prompts, each scoped to a
specific milestone with an explicit non-goals list. If you're
wondering why a module has a "No business logic yet" or "Deferred to
Phase N" comment, that's this discipline in action — every prompt
builds exactly its own scope and explicitly defers everything else,
rather than half-building future work speculatively. `git log` and each
module's docstring will tell you which prompt introduced it.

## Before Your First Pull Request

See `CONTRIBUTING.md` for the full checklist. In short: `scripts/validate.sh`
must pass locally before you push (it runs the same fast checks CI
runs first), and every PR needs a linked requirement — a change with no
traceable requirement is a signal the change's scope isn't grounded in
the CES, per
[97_CICD_Architecture.md](../architecture/specification/97_CICD_Architecture.md).

## Who Owns What

See `.github/CODEOWNERS` for the current, authoritative mapping. This
is a small team at this milestone — when in doubt, ask rather than
guess.
