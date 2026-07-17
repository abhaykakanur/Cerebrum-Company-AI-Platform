# Cerebrum

**Enterprise Knowledge Intelligence Platform.**

> Transforming fragmented organizational knowledge into trustworthy
> enterprise intelligence — the central intelligence layer of an
> organization, grounding AI reasoning in permission-aware, citation-backed
> enterprise data.

[![License: Unspecified](https://img.shields.io/badge/license-unspecified-lightgrey.svg)](LICENSE)

## What Is This Repository

This is the implementation of Cerebrum, built against the **Cerebrum
Engineering Specification (CES)** — a complete, 108-document architectural
specification covering product vision, functional requirements, system
architecture, data architecture, AI architecture, connector and search
architecture, security and API architecture, frontend architecture, and
engineering standards. The CES is the single source of truth this codebase
implements; it does not redesign it. See
[`docs/architecture/specification/`](docs/architecture/specification/README.md)
for the full specification, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for
what that means for how you work in this repository.

**Current status:** Repository Foundation. No business functionality is
implemented yet — this is the engineering scaffold every future
implementation phase builds on. See
[`docs/architecture/specification/110_Implementation_Roadmap.md`](docs/architecture/specification/110_Implementation_Roadmap.md)
for what comes next.

## Repository Structure

```
cerebrum/
├── apps/
│   ├── backend/          # Python/FastAPI modular monolith
│   └── frontend/         # Next.js/TypeScript frontend
├── packages/              # Shared TypeScript packages (types, config, utils, tooling)
├── infrastructure/
│   └── docker/            # Local infrastructure (PostgreSQL, Neo4j, Qdrant, Redis, MinIO, OpenSearch)
├── docs/
│   ├── architecture/      # Repository architecture docs + the CES specification
│   ├── development/       # Getting started, dev workflow, coding standards
│   ├── deployment/        # Infrastructure and deployment guides
│   ├── api/                # API documentation (populated once endpoints exist)
│   └── testing/            # Testing strategy documentation
├── scripts/                # Developer commands (setup, start, test, validate, ...)
├── config/                  # Per-environment configuration
├── .github/                  # Issue/PR templates, CODEOWNERS
├── .vscode/                   # Shared editor configuration
└── .devcontainer/               # GitHub Codespaces / VS Code Dev Containers config
```

See [`docs/architecture/folder-structure.md`](docs/architecture/folder-structure.md)
for the complete, annotated tree.

## Quick Start

```bash
git clone <repository-url> cerebrum
cd cerebrum
scripts/setup.sh
```

This installs dependencies for both workspaces, provisions your local
`.env`, and starts the infrastructure stack. Then:

```bash
scripts/doctor.sh          # verify everything is healthy
pnpm --filter @cerebrum/frontend dev   # frontend dev server
uv run pytest apps/backend/tests       # backend tests
```

See [`docs/development/getting-started.md`](docs/development/getting-started.md)
for the full walkthrough and
[`docs/deployment/local-development.md`](docs/deployment/local-development.md)
for the complete infrastructure command reference.

## Technology Stack

Python 3.12 + FastAPI (backend) · Next.js + TypeScript + Tailwind
(frontend) · PostgreSQL, Neo4j, Qdrant, Redis, MinIO, OpenSearch
(polyglot persistence) · uv + pnpm (package management). See
[`docs/development/technology-stack.md`](docs/development/technology-stack.md)
for the full stack and
[`docs/architecture/specification/32_Technology_Stack.md`](docs/architecture/specification/32_Technology_Stack.md)
for the architectural justification behind every choice.

## Documentation Map

| I want to... | Read |
|---|---|
| Understand the product and its full architecture | [`docs/architecture/specification/`](docs/architecture/specification/README.md) |
| Get my environment running | [`docs/development/getting-started.md`](docs/development/getting-started.md) |
| Understand how this repo is organized | [`docs/architecture/repository-architecture.md`](docs/architecture/repository-architecture.md) |
| Know what I can and can't import from where | [`docs/architecture/dependency-rules.md`](docs/architecture/dependency-rules.md) |
| Run local infrastructure | [`docs/deployment/local-development.md`](docs/deployment/local-development.md) |
| Contribute a change | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Report a security issue | [`SECURITY.md`](SECURITY.md) |

## License

See [`LICENSE`](LICENSE) — not yet finalized. Treat this repository as
proprietary and confidential until that file is replaced.
