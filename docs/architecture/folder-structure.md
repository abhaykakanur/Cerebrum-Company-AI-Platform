# Folder Structure

Complete, annotated repository tree as of the Enterprise Data &
Infrastructure Foundation milestone (Phase 1, Prompt 4). Directories
that are still empty of code (structural placeholders for future
*business* work — no domain has been implemented yet) are marked
accordingly — each such directory contains a `README.md` explaining what
belongs there and why it's empty now.

```
cerebrum/
├── apps/
│   ├── backend/
│   │   ├── alembic/                # Migration environment (empty versions/ — no ORM model yet)
│   │   ├── alembic.ini
│   │   ├── src/cerebrum/
│   │   │   ├── api/              # FastAPI routers: health, /api/v1, response envelope schemas
│   │   │   ├── application/       # Use cases, command/query handlers (empty — no business use case yet)
│   │   │   ├── config/             # Typed, validated, environment-driven settings (populated)
│   │   │   ├── core/                 # Application Factory, lifecycle, logging, exception handlers (populated)
│   │   │   ├── dependencies/          # FastAPI DI providers: settings, logger, state, infra clients
│   │   │   ├── domain/                 # Entities, aggregates, domain services (empty — no domain yet)
│   │   │   ├── events/                  # DomainEvent base + in-process EventDispatcher (interfaces only)
│   │   │   ├── infrastructure/            # DB/cache/graph/vector/storage/search client managers (populated)
│   │   │   ├── middleware/                 # Request ID/Correlation ID/context/timing/logging pipeline (populated)
│   │   │   ├── repositories/                # Abstract CRUD/pagination/sort/filter/soft-delete contracts (populated — no concrete repository yet)
│   │   │   ├── services/                     # Cross-domain composed services (empty — no service yet)
│   │   │   ├── shared/                         # Error taxonomy (shared/errors/) + future cross-cutting utilities
│   │   │   ├── utils/                            # Clock, UUID generation (populated)
│   │   │   ├── workers/                            # Worker/Job/Queue/Scheduler interfaces only — no implementation
│   │   │   └── main.py                               # ASGI entrypoint — delegates to core.factory only
│   │   ├── tests/{unit,integration,e2e,performance,ai_evaluation}/  # unit/ has platform + infrastructure tests; rest empty
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
│   │   └── adrs/                   # Future implementation-phase ADRs (ADR-021+)
│   ├── development/                  # This document's siblings
│   ├── deployment/                     # Infrastructure/deployment guides
│   ├── api/                              # Reserved — populated once API endpoints exist
│   └── testing/                            # Reserved — populated as test suites grow
│
├── scripts/            # Developer commands (setup, start, test, validate, ...)
├── config/{development,testing,staging,production}/   # Per-environment config (empty — reserved)
├── tools/                 # Reserved for future custom developer tooling
├── tests/{unit,integration,e2e,performance,ai-evaluation}/  # Cross-cutting, full-stack tests (empty)
├── examples/                 # Reserved for future usage examples
├── assets/                     # Reserved for shared static assets
│
├── .github/                       # Issue/PR templates, CODEOWNERS, workflow placeholders
├── .vscode/                          # Shared editor configuration
├── .devcontainer/                       # Codespaces / Dev Containers config
│
├── README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, LICENSE
├── package.json, pnpm-workspace.yaml     # TypeScript workspace root
├── pyproject.toml                          # Python (uv) workspace root
├── .env.example, .gitignore, .gitattributes, .editorconfig, .pre-commit-config.yaml
```

## Why So Many Empty, README-Only Directories

`domain/`, `application/`, and `services/` remain documentation-only:
they hold business logic, and no business domain has been implemented
yet (see CIS Phase 1 Prompt 4's Non-Objectives). `api/`, `config/`,
`core/`, `dependencies/`, `events/`, `middleware/`, `shared/`, `utils/`,
`infrastructure/`, and `repositories/` are now populated — they hold the
reusable platform every future domain builds on, per that same prompt's
Primary Objectives. `infrastructure/` and `repositories/` specifically
hold *connection management and contracts*, not business queries or
concrete repositories — see `docs/architecture/infrastructure/README.md`.

Every one of these directories exists because the CES's architecture
already specifies it belongs there (see
`docs/architecture/specification/33_Directory_Structure.md` for the
backend's originally-specified layout, adapted slightly at
implementation time — see `docs/architecture/repository-architecture.md`
for that adaptation). Creating the structure now, with each directory's
purpose documented in its own `README.md`, means later implementation
work drops code into an already-agreed location instead of inventing
structure ad hoc mid-feature.
