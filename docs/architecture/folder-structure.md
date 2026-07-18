# Folder Structure

Complete, annotated repository tree as of the Production Readiness &
Platform Hardening milestone (Phase 1, Prompt 7) — Phase 1's final
milestone. Directories that
are still empty of code (structural placeholders for future *business*
work — no domain has been implemented yet) are marked accordingly — each
such directory contains a `README.md` explaining what belongs there and
why it's empty now.

```
cerebrum/
├── apps/
│   ├── backend/
│   │   ├── alembic/                # Migration environment — one hand-written revision (identity/security tables)
│   │   ├── alembic.ini
│   │   ├── src/cerebrum/
│   │   │   ├── api/              # FastAPI routers: health, /api/versions, /api/v1, /api/v1/auth, response envelope + builder, versioning, OpenAPI error docs
│   │   │   ├── application/       # application/auth/ (login, RBAC, API keys, audit) — no other use case yet
│   │   │   ├── config/             # Typed, validated, environment-driven settings (populated)
│   │   │   ├── core/                 # Application Factory, lifecycle, logging, exception handlers, OpenAPI/metadata (populated)
│   │   │   ├── dependencies/          # FastAPI DI providers: settings, logger, state, infra clients, auth, pagination, request context, rate limiting
│   │   │   ├── domain/                 # Entities, aggregates, domain services (empty — no domain yet)
│   │   │   ├── events/                  # DomainEvent base + in-process EventDispatcher (interfaces only)
│   │   │   ├── infrastructure/            # DB/cache/graph/vector/storage/search clients + database/models/ + security/ + storage/files.py (populated)
│   │   │   ├── middleware/                 # Request ID/Correlation ID/context/timing/logging/authentication/size-limit/metrics pipeline (populated)
│   │   │   ├── repositories/                # Abstract contracts + repositories/postgres/ (identity/security models)
│   │   │   ├── services/                     # Cross-domain composed services (empty — no service yet)
│   │   │   ├── shared/                         # Error taxonomy (shared/errors/) + future cross-cutting utilities
│   │   │   ├── utils/                            # Clock, UUID generation (populated)
│   │   │   ├── workers/                            # Worker/Job/Queue/Scheduler interfaces only — no implementation
│   │   │   └── main.py                               # ASGI entrypoint — delegates to core.factory only
│   │   ├── tests/{unit,integration,e2e,performance,ai_evaluation}/  # unit/ has 246 platform + infra + identity/security tests; rest empty
│   │   ├── Dockerfile                # Production container image — see docs/deployment/production-deployment.md
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── frontend/
│       ├── app/                    # Next.js App Router (placeholder layout + page only)
│       ├── components/               # Design System components (empty)
│       ├── features/                   # Feature modules (empty)
│       ├── hooks/                        # Shared React hooks (empty)
│       ├── layouts/                        # Layout System primitives (empty)
│       ├── lib/                              # API client (empty)
│       ├── providers/                          # React context providers (empty)
│       ├── services/                             # Frontend service layer (empty)
│       ├── styles/                                 # Global styles beyond Tailwind (empty)
│       ├── types/                                    # Frontend-local types (empty)
│       ├── utils/                                      # Generic helpers (empty)
│       ├── public/                                       # Static assets (empty)
│       ├── tests/{unit,integration,e2e,performance}/       # empty
│       ├── package.json, tsconfig.json, next.config.js, tailwind.config.ts
│       └── README.md
│
├── packages/
│   ├── shared-types/       # Frontend-facing shared TS types (empty index)
│   ├── shared-config/       # Non-secret shared config constants (empty index)
│   ├── shared-utils/          # Dependency-free shared TS utilities (empty index)
│   ├── eslint-config/           # Shared ESLint rules (populated — base + next + library)
│   └── tsconfig/                  # Shared tsconfig bases (populated)
│
├── infrastructure/
│   └── docker/               # Local infrastructure — see docs/deployment/
│
├── docs/
│   ├── architecture/           # This directory
│   │   ├── specification/        # The complete CES (108 documents)
│   │   ├── infrastructure/         # Database/connection-lifecycle/transaction/repository/migration guides
│   │   ├── security/                 # Authentication/RBAC/multi-tenancy/API key/security-architecture guides
│   │   ├── api/                        # API architecture/versioning/dependency/response/validation guides
│   │   └── adrs/                       # Future implementation-phase ADRs (ADR-021+)
│   ├── development/                  # Getting started, onboarding, dev workflow, coding standards
│   ├── deployment/                     # Infrastructure + production deployment guides, troubleshooting
│   ├── api/                              # Reserved — populated once business API endpoints exist (distinct from docs/architecture/api/, the platform's own architecture docs)
│   └── testing/                            # Testing Guide (populated — see docs/testing/README.md)
│
├── scripts/            # Developer commands (setup, start, test, validate, ...)
├── config/{development,testing,staging,production}/   # Per-environment config (empty — reserved)
├── tools/                 # Reserved for future custom developer tooling
├── tests/{unit,integration,e2e,performance,ai-evaluation}/  # Cross-cutting, full-stack tests (empty)
├── examples/                 # Reserved for future usage examples
├── assets/                     # Reserved for shared static assets
│
├── .github/
│   └── workflows/ci.yml               # Real CI pipeline (format/lint/typecheck/test/security/docker-build)
├── .vscode/                          # Shared editor configuration
├── .devcontainer/                       # Codespaces / Dev Containers config
│
├── README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, LICENSE
├── package.json, pnpm-workspace.yaml     # TypeScript workspace root
├── pyproject.toml                          # Python (uv) workspace root
├── .env.example, .gitignore, .gitattributes, .editorconfig, .pre-commit-config.yaml, .dockerignore
```

## Why So Many Empty, README-Only Directories

`domain/` and `services/` remain documentation-only: they hold business
logic, and no business domain has been implemented yet (see CIS Phase 1
Prompt 5's Non-Objectives). `application/` now has one subpackage
(`application/auth/`) — platform authentication/authorization services,
not a business use case; it remains otherwise empty. `api/`, `config/`,
`core/`, `dependencies/`, `events/`, `middleware/`, `shared/`, `utils/`,
`infrastructure/`, and `repositories/` are populated — they hold the
reusable platform every future domain builds on. `infrastructure/` and
`repositories/` hold *connection management, contracts, and the
identity/security models* specifically — see
`docs/architecture/infrastructure/README.md` and
`docs/architecture/security/README.md` — not business queries or a
business domain's own repositories. As of Phase 1, Prompt 6, `api/`,
`dependencies/`, and `middleware/` also hold the reusable API platform
layer (pagination/filtering/sorting, response standardization, API
versioning, OpenAPI documentation, general-purpose rate limiting, API
metrics) — see `docs/architecture/api/README.md` — still no business
endpoint or query.

Every one of these directories exists because the CES's architecture
already specifies it belongs there (see
`docs/architecture/specification/33_Directory_Structure.md` for the
backend's originally-specified layout, adapted slightly at
implementation time — see `docs/architecture/repository-architecture.md`
for that adaptation). Creating the structure now, with each directory's
purpose documented in its own `README.md`, means later implementation
work drops code into an already-agreed location instead of inventing
structure ad hoc mid-feature.
