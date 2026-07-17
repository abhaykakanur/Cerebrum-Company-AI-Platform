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

| Concern | Read |
|---|---|
| System architecture (Modular Monolith, 15 components) | `docs/architecture/specification/30_System_Architecture.md` |
| Universal architecture principles (Clean/Hexagonal/DDD) | `docs/architecture/specification/34_Architecture_Principles.md` |
| Per-domain architecture (all 30 domains) | `docs/architecture/specification/35_Domain_Architecture.md` |
| Data architecture (polyglot persistence, tenancy) | `docs/architecture/specification/41_Data_Architecture.md` onward |
| AI architecture | `docs/architecture/specification/50_AI_Architecture.md` onward |
| Security architecture | `docs/architecture/specification/75_Security_Architecture.md` onward |
| API architecture | `docs/architecture/specification/80_API_Architecture.md` onward |
| Frontend architecture | `docs/architecture/specification/85_Frontend_Architecture.md` onward |

## How This Repository Maps to That Architecture

| CES Concept | This Repository |
|---|---|
| Backend Layer, AI Layer, Retrieval Layer, Knowledge Layer, etc. (15 components) | `apps/backend/src/cerebrum/` — see `docs/architecture/layer-responsibilities.md` |
| Frontend Layer | `apps/frontend/` |
| Persistence Layer (5 datastores + OpenSearch) | `infrastructure/docker/` (local) |
| 30 functional domains | Subpackages within `apps/backend/src/cerebrum/domain/`, `application/`, `infrastructure/` — added incrementally per `docs/architecture/specification/110_Implementation_Roadmap.md` |
| API Domain | `apps/backend/src/cerebrum/api/` |

## Current Implementation Status

Repository Foundation and Infrastructure Foundation only — see the root
`README.md`'s status note. No domain has been implemented yet.
`docs/architecture/module-ownership.md` will be updated as each domain is
added.
