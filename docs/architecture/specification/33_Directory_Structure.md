# 33 — Directory Structure

## Purpose

This document defines the production-grade repository structure for Cerebrum, enforcing the clean dependency flow (domain → application → infrastructure) established in [30_System_Architecture.md](30_System_Architecture.md) and [31_Component_Architecture.md](31_Component_Architecture.md), and mapping the 30 functional domains from [20_Functional_Requirements.md](20_Functional_Requirements.md) onto concrete filesystem locations.

## Scope

This document covers directory and package layout only. It does not define file-level contents, class names, or code. Directory names below are illustrative and binding as an architectural contract for dependency direction; exact naming conventions (e.g., snake_case vs. kebab-case) are Deferred to Architecture-time implementation style guides.

## Definitions

See [10_Glossary.md](10_Glossary.md) and [30_System_Architecture.md](30_System_Architecture.md). No new terms are introduced here.

## Repository Root Structure

```
cerebrum/
├── frontend/                    # Frontend Layer — Next.js/React/TypeScript
├── backend/                     # Backend Layer and all domain-owning components
├── connectors/                  # Connector Layer — one plugin package per source system
├── docs/                        # This CES specification set (Parts 1–3 and beyond)
├── scripts/                     # One-off and operational scripts (migrations, seed data, admin tooling)
├── config/                      # Environment-specific configuration templates (see 37_Configuration_Strategy.md)
├── deployment/                  # Docker Compose, Kubernetes manifests, infrastructure-as-code
└── tests/                       # Cross-cutting test suites (e2e); component-local tests live with their component
```

## Frontend Layer

```
frontend/
├── app/                         # Next.js app-router pages (Conversation, Search, Documents, Graph, Admin)
├── components/                  # Shared, reusable UI components
├── lib/
│   ├── api-client/              # Typed client for the Public/Administrative API (API Domain contract)
│   └── hooks/                   # Shared React hooks
├── styles/
└── tests/
    ├── unit/                    # Vitest unit tests
    └── e2e/                     # Playwright end-to-end tests (may also live in root tests/e2e/)
```

## Backend Layer

The backend follows the universal domain/application/infrastructure layering from [31_Component_Architecture.md](31_Component_Architecture.md) at two levels: a shared `core/` for cross-cutting primitives, and one package per functional domain, grouped by the fifteen high-level components for navigability.

```
backend/
├── core/                        # Shared kernel: base entity/value-object classes, error types,
│   │                            # dependency-injection container, logging/tracing instrumentation import surface
│   ├── domain/                  # Base DDD building blocks (Entity, ValueObject, AggregateRoot, DomainEvent)
│   ├── errors/                  # Error taxonomy (see 38_Observability.md)
│   └── di/                      # Dependency injection composition root
│
├── identity/                    # Component: Backend Layer — Identity, Workspace, Organization Domains
│   ├── identity/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── workspace/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   └── organization/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── users/                       # Component: Backend Layer — User Management Domain
│   └── user_management/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── auth/                        # Component: Authentication Layer + Authorization Layer
│   ├── authentication/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   └── authorization/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── knowledge/                   # Component: Knowledge Layer — largest component, one subpackage per domain
│   ├── ingestion/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── processing/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── storage/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── graph/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── memory/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── meeting_intelligence/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── decision_intelligence/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   └── pipeline/                # Shared ingestion → processing → graph-extraction orchestration
│
├── search/                      # Component: Retrieval Layer + Enterprise Search (query side)
│   ├── enterprise_search/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   └── retrieval/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── ai/                          # Component: AI Layer — Reasoning, Citation, Confidence Domains
│   ├── reasoning/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/       # LLMProviderPort adapters
│   ├── citation/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   └── confidence/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── conversation/                # Component: Backend Layer — Conversation Domain
│   └── conversation/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── documents/                   # Component: Backend Layer — Document Management Domain
│   └── document_management/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── expertise/                   # Component: Backend Layer — Expertise Discovery Domain
│   └── expertise_discovery/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── analytics/                   # Component: Analytics Layer
│   └── analytics/
│       ├── application/
│       └── infrastructure/
│
├── administration/               # Component: Administration Layer
│   └── administration/
│       └── application/          # Thin composition layer — see 31_Component_Architecture.md
│
├── configuration/                # Component: Configuration Layer
│   └── configuration/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── notification/                 # Component: Backend Layer — Notification Domain
│   └── notification/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── audit/                        # Component: Backend Layer — Audit Domain
│   └── audit/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── monitoring/                   # Component: Monitoring Layer
│   ├── health/
│   └── instrumentation/          # Shared logging/metrics/tracing import surface
│
├── infrastructure/               # Component: Infrastructure Layer — cross-cutting, non-domain-specific
│   ├── security/                 # Secrets, encryption key access (FR-SC-001–003)
│   ├── persistence/               # Component: Persistence Layer
│   │   ├── postgres/
│   │   ├── neo4j/
│   │   ├── qdrant/
│   │   ├── opensearch/
│   │   ├── redis/
│   │   └── minio/
│   ├── api_versioning/
│   └── webhooks/
│
├── background/                   # Component: Background Processing Layer
│   ├── tasks/                     # Task definitions (sync, pipeline stages, retention sweep, staleness scan)
│   ├── scheduler/
│   └── infrastructure/            # Celery/broker adapter (see 32_Technology_Stack.md, 36_Background_Processing.md)
│
├── api/                           # Component: API Domain implementation (part of Backend Layer)
│   ├── public/                    # Public API routers (FastAPI)
│   ├── internal/                  # Internal service-to-service API routers
│   ├── administrative/            # Administrative API routers
│   └── connector/                 # Connector API routers (FR-AP-004)
│
└── tests/
    ├── unit/                      # Mirrors backend/ package structure; tests domain/application in isolation
    └── integration/                # Tests infrastructure adapters against real or containerized datastores
```

## Connector Layer

```
connectors/
├── framework/                    # ConnectorPort interface, shared sync orchestration, retry/conflict handling
│   ├── domain/
│   └── application/
├── slack/                        # One package per supported connector category (FR-CN-011)
├── microsoft_teams/
├── google_drive/
├── onedrive/
├── sharepoint/
├── confluence/
├── notion/
├── github/
├── gitlab/
├── jira/
├── linear/
├── google_calendar/
├── outlook_calendar/
├── gmail/
├── outlook_mail/
├── dropbox/
├── box/
├── s3/
├── local_filesystem/
├── postgresql/
├── mysql/
├── mongodb/
├── rest_api/                     # Generic REST API connector
└── tests/
    └── unit/                     # Per-connector unit tests, one subfolder per connector package
```

## Deployment

```
deployment/
├── docker/
│   ├── docker-compose.yml        # Full local stack: backend, frontend, Postgres, Neo4j, Qdrant,
│   │                             # OpenSearch, Redis, MinIO
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── kubernetes/
    ├── base/                     # Kustomize/Helm base manifests (Deferred to Architecture for tool choice)
    └── overlays/
        ├── staging/
        └── production/
```

## Configuration and Scripts

```
config/
├── .env.example                  # Template only — no secret values (see 37_Configuration_Strategy.md)
├── logging.yaml
└── feature_flags.default.yaml

scripts/
├── migrate.sh                    # Alembic migration runner
├── seed_dev_data.py
└── admin/                        # One-off administrative scripts, never a substitute for API Domain surfaces
```

## Dependency Flow Enforcement

The directory structure encodes the following non-negotiable rules, enforced by import-linting tooling at CI time (Deferred to Architecture for the specific linter):

1. **`domain/` imports nothing from `application/` or `infrastructure/`**, within its own package or any other.
2. **`application/` imports only from its own package's `domain/`** and from other domains' published `application/` service interfaces — never another domain's `infrastructure/` or internal `domain/` submodules directly.
3. **`infrastructure/` imports from its own package's `domain/` and `application/`** to implement their ports, and may import external libraries/SDKs freely.
4. **No package under `backend/` imports from `frontend/`**, and `frontend/` imports only from its own `lib/api-client/`, never from any `backend/` package directly (this is enforced by the two being deployed as separate processes, not merely by convention).
5. **`connectors/<name>/` packages import only from `connectors/framework/`** and general-purpose libraries — never from `backend/knowledge/` or any other backend package directly; connector output crosses into the Knowledge Layer only through the framework's defined handoff contract.

## Responsibilities

- Every new domain added in a later phase must receive its own `domain/`, `application/`, `infrastructure/` triad under the directory structure above, placed within the high-level component it belongs to per [30_System_Architecture.md](30_System_Architecture.md).
- CI tooling enforcing the Dependency Flow Enforcement rules above is a required part of the build pipeline before this structure is considered actually binding rather than aspirational — consistent with the Non-Negotiable Extraction Seam constraint in [30_System_Architecture.md](30_System_Architecture.md).

## Constraints

- This structure does not dictate a specific Python packaging tool (Poetry, uv, pip-tools) or monorepo tool (Nx, Turborepo) — Deferred to Architecture.
- Directory names are illustrative of the required separation, not a naming-convention mandate beyond that separation.

## Future Considerations

- If a component is extracted into an independent service per the extraction-seam guidance in [31_Component_Architecture.md](31_Component_Architecture.md), its directory subtree is expected to move to its own repository largely unchanged, with only its `infrastructure/` adapter layer gaining a network-facing entry point.

## Acceptance Criteria

- [ ] Every domain from [20_Functional_Requirements.md](20_Functional_Requirements.md) has an explicit location in this structure.
- [ ] Every one of the fifteen high-level components from [30_System_Architecture.md](30_System_Architecture.md) is identifiable in the structure.
- [ ] The dependency-flow rules are stated as enforceable (tooling-checked), not merely descriptive.
