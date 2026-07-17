# Folder Structure

Complete, annotated repository tree as of Repository Foundation +
Infrastructure Foundation. Directories that are currently empty of code
(structural placeholders for future work) are marked accordingly — each
such directory contains a `README.md` explaining what belongs there and
why it's empty now.

```
cerebrum/
├── apps/
│   ├── backend/
│   │   ├── src/cerebrum/
│   │   │   ├── api/              # FastAPI routers (empty — no endpoints yet)
│   │   │   ├── application/       # Use cases, command/query handlers (empty)
│   │   │   ├── config/             # Settings loading (empty)
│   │   │   ├── core/                 # Shared kernel: base types, error taxonomy, DI root (empty)
│   │   │   ├── dependencies/          # FastAPI DI providers (empty)
│   │   │   ├── domain/                 # Entities, aggregates, domain services (empty)
│   │   │   ├── events/                  # Domain events (empty)
│   │   │   ├── infrastructure/            # Adapters: DB, LLM, secrets, etc. (empty)
│   │   │   ├── middleware/                 # Auth/tenant/tracing middleware (empty)
│   │   │   ├── repositories/                # Repository adapter implementations (empty)
│   │   │   ├── services/                     # Cross-domain composed services (empty)
│   │   │   ├── shared/                         # Cross-cutting, non-domain utilities (empty)
│   │   │   ├── utils/                            # Generic, dependency-free helpers (empty)
│   │   │   └── workers/                            # Background Processing workers (empty)
│   │   ├── tests/{unit,integration,e2e,performance,ai_evaluation}/  # empty
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

Every currently-empty directory exists because the CES's architecture
already specifies it belongs there (see
`docs/architecture/specification/33_Directory_Structure.md` for the
backend's originally-specified layout, adapted slightly at
implementation time — see `docs/architecture/repository-architecture.md`
for that adaptation). Creating the structure now, with each directory's
purpose documented in its own `README.md`, means later implementation
work drops code into an already-agreed location instead of inventing
structure ad hoc mid-feature.
