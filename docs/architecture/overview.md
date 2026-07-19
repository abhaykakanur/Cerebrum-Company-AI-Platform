# Architecture Overview

## The Short Version

Cerebrum is built as a **Modular Monolith**: one deployable backend
application, internally partitioned into 30 strictly-isolated functional
domains grouped into 15 high-level components, following Clean/Hexagonal
Architecture and Domain-Driven Design. A Next.js frontend consumes it
exclusively through a versioned REST API. Five purpose-specific datastores
(PostgreSQL, Neo4j, Qdrant, Redis, MinIO) plus OpenSearch form a polyglot
persistence layer, each with exactly one responsibility.

This is a summary for orientation. The authoritative, complete
architecture is the CES — this document does not restate it, it maps you
into it.

## Where the Real Architecture Lives

| Concern                                                 | Read                                                                 |
| ------------------------------------------------------- | -------------------------------------------------------------------- |
| System architecture (Modular Monolith, 15 components)   | `docs/architecture/specification/30_System_Architecture.md`          |
| Universal architecture principles (Clean/Hexagonal/DDD) | `docs/architecture/specification/34_Architecture_Principles.md`      |
| Per-domain architecture (all 30 domains)                | `docs/architecture/specification/35_Domain_Architecture.md`          |
| Data architecture (polyglot persistence, tenancy)       | `docs/architecture/specification/41_Data_Architecture.md` onward     |
| AI architecture                                         | `docs/architecture/specification/50_AI_Architecture.md` onward       |
| Security architecture                                   | `docs/architecture/specification/75_Security_Architecture.md` onward |
| API architecture                                        | `docs/architecture/specification/80_API_Architecture.md` onward      |
| Frontend architecture                                   | `docs/architecture/specification/85_Frontend_Architecture.md` onward |

## How This Repository Maps to That Architecture

| CES Concept                                                                     | This Repository                                                                                                                                                                     |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Layer, AI Layer, Retrieval Layer, Knowledge Layer, etc. (15 components) | `apps/backend/src/cerebrum/` — see `docs/architecture/layer-responsibilities.md`                                                                                                    |
| Frontend Layer                                                                  | `apps/frontend/`                                                                                                                                                                    |
| Persistence Layer (5 datastores + OpenSearch)                                   | `infrastructure/docker/` (local)                                                                                                                                                    |
| 30 functional domains                                                           | Subpackages within `apps/backend/src/cerebrum/domain/`, `application/`, `infrastructure/` — added incrementally per `docs/architecture/specification/110_Implementation_Roadmap.md` |
| API Domain                                                                      | `apps/backend/src/cerebrum/api/`                                                                                                                                                    |

## Current Implementation Status

**Phase 1 (Foundation) is complete** as of CIS Phase 1 Prompt 7
(Production Readiness & Platform Hardening) — see the root `README.md`'s
status note. Seven milestones: Repository Foundation, Infrastructure
Foundation (Docker Compose), Enterprise Backend Platform Foundation,
Enterprise Data & Infrastructure Foundation, Identity, Security &
Multi-Tenancy Foundation, Enterprise API Platform & Developer Experience,
and Production Readiness & Platform Hardening. The backend now runs
(typed configuration, DI, middleware, logging, exception handling,
health endpoints with version/build information), connects to all six
datastores at startup with retry and graceful degradation, provides JWT
authentication, RBAC, API keys, and multi-tenant request context, a
reusable API platform layer (pagination/filtering/sorting, response
standardization, API versioning, OpenAPI documentation, general-purpose
rate limiting, API metrics and tracing hooks), and is now
production-hardened: a validated architecture (no circular imports, no
layering violations, no duplicate abstractions — verified
programmatically), a production Docker image
(`apps/backend/Dockerfile`), a real CI pipeline
(`.github/workflows/ci.yml`: formatting, linting, `mypy --strict`, unit
tests with coverage, secret/dependency scanning, Docker build
verification), and enforced production configuration safety (the
process refuses to start with an unrotated default credential or a
wildcard trusted-host/CORS policy in `staging`/`production`) — see
`apps/backend/README.md`, `docs/architecture/infrastructure/`,
`docs/architecture/security/`, `docs/architecture/api/`, and
`docs/deployment/production-deployment.md`. Every business domain this
platform foundation was built for is now implemented on top of it
(documents/processing, knowledge graph, semantic search, retrieval/RAG,
AI chat, connectors, workflows, Employee Knowledge Capsules — see
`docs/api/README.md`), along with a Next.js frontend implementing every
major feature area against them (`apps/frontend/README.md`).
`docs/architecture/module-ownership.md` reflects each domain as it was
added.
