# Local Development Guide

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (`docker compose`, not the legacy `docker-compose`)
- [Node.js](https://nodejs.org/) 20+ and [pnpm](https://pnpm.io/) 9+
- [uv](https://docs.astral.sh/uv/) (Python package/environment manager)
- Git

## First-Time Setup

```bash
git clone <repository-url> cerebrum
cd cerebrum
scripts/setup.sh
```

`scripts/setup.sh` installs frontend and backend dependencies, installs
pre-commit hooks, provisions your local `.env` from `.env.example`, and
starts the infrastructure stack. See `scripts/setup.sh` for exactly what
it does — it is a thin, readable wrapper, not a black box.

## Day-to-Day Commands

| Command | What it does |
|---|---|
| `scripts/start.sh` | Start all infrastructure services in the background. |
| `scripts/stop.sh` | Stop all services. Data volumes are preserved. |
| `scripts/reset.sh` | Stop all services **and permanently delete all data volumes**. Prompts for confirmation. |
| `scripts/logs.sh [service]` | Follow logs for all services, or one (e.g., `scripts/logs.sh postgres`). |
| `scripts/doctor.sh` | Check the health of every service; exits non-zero if anything is unhealthy. |
| `scripts/format.sh` | Format all Python and TypeScript code in place. |
| `scripts/lint.sh` | Lint all code. Fails on any warning. |
| `scripts/typecheck.sh` | Type-check Python (mypy) and TypeScript (tsc), both in strict mode. |
| `scripts/test.sh` | Run unit tests. `scripts/test.sh --all` also runs integration/e2e (requires infrastructure running). |
| `scripts/validate.sh` | Run format-check + lint + typecheck + unit tests, in that order — the pre-push sanity check. |
| `scripts/clean.sh` | Remove build artifacts and dependency directories (not infrastructure data — see `reset.sh`). |

Equivalent `pnpm` aliases exist for the infrastructure commands
(`pnpm infra:up`, `pnpm infra:down`, `pnpm infra:reset`, `pnpm infra:logs`,
`pnpm infra:doctor`) if you prefer a single toolchain entry point — see
root `package.json`.

## Verifying Everything Works

```bash
scripts/start.sh
scripts/doctor.sh
```

Expected output: all six services report healthy. First start can take up
to a minute (OpenSearch and Neo4j are the slowest to initialize).

You can also inspect each service directly:

- **Neo4j Browser:** <http://localhost:7474>
- **MinIO Console:** <http://localhost:9001>
- **OpenSearch cluster health:** <http://localhost:9200/_cluster/health>
- **Qdrant collections:** <http://localhost:6333/collections> (empty list is expected — no collections exist yet)

## Stopping Work for the Day

```bash
scripts/stop.sh
```

Your data (any test documents, graph state, etc. you created) is
preserved in Docker volumes and will still be there next time you run
`scripts/start.sh`.

## Starting Completely Fresh

```bash
scripts/reset.sh
scripts/start.sh
```

## What's *Not* Here Yet

This milestone provisions infrastructure only. There is no backend
server, no frontend dev server, and no application data — see
`docs/architecture/specification/110_Implementation_Roadmap.md` for what
comes next and when.
