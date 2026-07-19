# Getting Started

## Prerequisites

| Tool                                          | Version    | Why                                                                     |
| --------------------------------------------- | ---------- | ----------------------------------------------------------------------- |
| [Docker](https://docs.docker.com/get-docker/) | Compose v2 | Runs local infrastructure — see `docs/deployment/local-development.md`. |
| [Node.js](https://nodejs.org/)                | 20+        | Frontend and shared TypeScript packages.                                |
| [pnpm](https://pnpm.io/)                      | 9+         | TypeScript workspace package manager.                                   |
| [uv](https://docs.astral.sh/uv/)              | latest     | Python package/environment manager.                                     |
| Git                                           | any recent | Version control.                                                        |

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
# Frontend dev server (http://localhost:3000)
pnpm --filter @cerebrum/frontend dev

# Backend dev server (http://localhost:8000 — see apps/backend/README.md)
uv run uvicorn cerebrum.main:app --reload

# Backend unit tests
uv run pytest apps/backend/tests -m unit

# Frontend unit tests
pnpm --filter @cerebrum/frontend test

# Everything at once (format check + lint + typecheck + unit tests)
scripts/validate.sh
```

With the backend running, `curl http://localhost:8000/health` and
`http://localhost:8000/api/v1/docs` should both respond. There is no
registration endpoint — accounts are provisioned out-of-band (see
`apps/backend/tests/unit/_auth_factories.py` for the pattern used in
tests, or seed one directly); once you have credentials, `/login` on the
frontend is the real sign-in flow, not `/api/v1/docs`'s "Authorize"
button.

## What You Should See

Both applications are real, running software — not scaffolding. What you
should see:

- The frontend serves a working login flow and, once authenticated with
  at least one workspace, the full application shell: Dashboard, AI
  Chat, Enterprise Search, Knowledge Graph, Document Explorer, Connector
  and Workflow Dashboards, Employee Knowledge Capsules, Administration,
  and Monitoring — see `apps/frontend/README.md` for the complete list
  and its "Known Limitations" section for what's deliberately scoped
  out.
- The backend starts, serves `/health` (with version and build
  information), `/live`, `/ready`, `/api/versions`, and `/api/v1/docs`
  (130+ routes across 21 domains — see `docs/api/README.md`), and every
  backend unit test passes (see `docs/testing/README.md`).
- All six infrastructure services report healthy via `scripts/doctor.sh`
  **and** the backend actually connects to all six at startup — `/health`
  reports each as `healthy` (or `unavailable` with a real error detail if
  something's actually down, never `not_configured`).
- JWT login/refresh/logout work end-to-end against a seeded user — see
  `docs/architecture/security/authentication-guide.md`.
- `scripts/validate.sh` passes with zero lint/type warnings.
- `docker build -f apps/backend/Dockerfile -t cerebrum-backend .` (from
  the repository root) succeeds — see
  `docs/deployment/production-deployment.md`.

If all of that is true, your environment is correctly set up. See
`docs/architecture/specification/110_Implementation_Roadmap.md` for what
gets built next (Phase 2 onward), and
`docs/development/onboarding.md` for a fuller orientation.

## Next Steps

- Read `docs/architecture/repository-architecture.md` to understand how
  the codebase is organized before writing any code.
- Read `docs/architecture/dependency-rules.md` — these rules are enforced
  in code review, not optional style guidance.
- Read `CONTRIBUTING.md` for the full contribution workflow.
