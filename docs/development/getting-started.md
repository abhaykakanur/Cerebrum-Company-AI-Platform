# Getting Started

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| [Docker](https://docs.docker.com/get-docker/) | Compose v2 | Runs local infrastructure — see `docs/deployment/local-development.md`. |
| [Node.js](https://nodejs.org/) | 20+ | Frontend and shared TypeScript packages. |
| [pnpm](https://pnpm.io/) | 9+ | TypeScript workspace package manager. |
| [uv](https://docs.astral.sh/uv/) | latest | Python package/environment manager. |
| Git | any recent | Version control. |

## Clone and Set Up

```bash
git clone <repository-url> cerebrum
cd cerebrum
scripts/setup.sh
```

`scripts/setup.sh` performs, in order:

1. Installs frontend/shared-package dependencies (`pnpm install`).
2. Installs backend dependencies (`uv sync`).
3. Installs pre-commit hooks.
4. Provisions your local `.env` from `.env.example`.
5. Starts the local infrastructure stack (PostgreSQL, Neo4j, Qdrant,
   Redis, MinIO, OpenSearch).

## Verify It Worked

```bash
scripts/doctor.sh
```

Expect all six infrastructure services to report healthy. First start can
take up to a minute. See `docs/deployment/troubleshooting.md` if
something doesn't come up cleanly.

## Run Things

```bash
# Frontend dev server (http://localhost:3000 — a placeholder page at this milestone)
pnpm --filter @cerebrum/frontend dev

# Backend unit tests
uv run pytest apps/backend/tests -m unit

# Everything at once (format check + lint + typecheck + unit tests)
scripts/validate.sh
```

## What You Should See

At this point in the project (Repository Foundation), there is no
application functionality yet — no login, no dashboard, no AI chat. What
you should see:

- The frontend serves a placeholder page confirming the build pipeline
  works.
- The backend package installs and imports cleanly with no errors.
- All six infrastructure services report healthy via `scripts/doctor.sh`.
- `scripts/validate.sh` passes with zero lint warnings.

If all of that is true, your environment is correctly set up. See
`docs/architecture/specification/110_Implementation_Roadmap.md` for what
gets built next.

## Next Steps

- Read `docs/architecture/repository-architecture.md` to understand how
  the codebase is organized before writing any code.
- Read `docs/architecture/dependency-rules.md` — these rules are enforced
  in code review, not optional style guidance.
- Read `CONTRIBUTING.md` for the full contribution workflow.
