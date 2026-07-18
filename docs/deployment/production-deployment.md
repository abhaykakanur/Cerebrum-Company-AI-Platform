# Production Deployment Guide

CIS Phase 1 Prompt 7's Production Readiness deliverable — how to build,
configure, and run the backend outside local development. See
[docker-architecture.md](docker-architecture.md) for the *local*
Docker Compose stack (datastores only) and
[96_Deployment_Strategy.md](../architecture/specification/96_Deployment_Strategy.md)
for the seven deployment models this architecture supports; this
document is the concrete "how," scoped to Container Deployment (the
model `apps/backend/Dockerfile` targets today).

## Building the Image

From the **repository root** (the build context must include both
`pyproject.toml` files):

```bash
docker build -f apps/backend/Dockerfile -t cerebrum-backend \
  --build-arg BUILD_COMMIT=$(git rev-parse HEAD) \
  --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  .
```

`BUILD_COMMIT`/`BUILD_TIME` are optional — omitted, the image reports
`"unknown"`/`"unknown"` on `GET /health` (see
`cerebrum.config.application.ApplicationSettings`). The CI pipeline
(`.github/workflows/ci.yml`'s `docker-build` job) passes them
automatically from `github.sha`.

See `apps/backend/Dockerfile`'s own header comment for the multi-stage
build's structure (dependency layer cached separately from source, a
non-root final image) and its note on why no `uv.lock` exists yet.

## Required Configuration

Every setting in `.env.example` has a local-development-safe default.
**None of them are production-safe as-is.** Before starting this image
in a staging/production environment, at minimum:

| Variable | Why it must change |
|---|---|
| `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `NEO4J_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Each defaults to `changeme-local-only` — see below, this is now an enforced startup failure, not just documentation. |
| `JWT_SIGNING_SECRET` | Defaults to a placeholder published in this very repository. An unrotated value lets anyone forge a valid access token. |
| `SECURITY_TRUSTED_HOSTS` | Defaults to `*`. Must be your real hostname(s). |
| `SECURITY_CORS_ALLOWED_ORIGINS` | Defaults to `http://localhost:3000`. Must be your real frontend origin(s), and must never contain `*`. |
| `ENVIRONMENT` | Must be `staging` or `production` — this is what activates every check below. |

### Startup Now Refuses to Boot on Default Secrets

As of CIS Phase 1 Prompt 7, `cerebrum.config.settings.Settings`'s
`_reject_default_secrets` validator raises
`ConfigurationException` — the process **will not start** — if
`ENVIRONMENT` is `staging`/`production` and any of the six credentials
above is still at its `changeme-local-only*` placeholder. This is a
deliberate, enforced gate, not advisory documentation: no invalid
configuration may allow the application to start, per
[37_Configuration_Strategy.md](../architecture/specification/37_Configuration_Strategy.md).
The same validator already rejected `SECURITY_TRUSTED_HOSTS=*` and
`SECURITY_CORS_ALLOWED_ORIGINS=*` in production since Phase 1, Prompt 3;
Prompt 7 extends it to every credential.

### Where Secrets Actually Come From in Production

Per [37_Configuration_Strategy.md](../architecture/specification/37_Configuration_Strategy.md),
a real deployment does not maintain a `.env` file on the host — secrets
are injected as environment variables by the orchestrator (e.g. a
Kubernetes `Secret` mounted as env vars, a cloud provider's secrets
manager integration) at container start. `.env.example`/`.env` remain a
local-development-only convenience; this image reads plain environment
variables either way, so both mechanisms work identically from the
application's point of view.

## Running the Container

```bash
docker run -d \
  --name cerebrum-backend \
  -p 8000:8000 \
  --env-file .env.production \
  cerebrum-backend
```

(`--env-file .env.production` is illustrative — see "Where Secrets
Actually Come From" above for why a real deployment typically injects
these individually rather than from a file on disk.)

## Health Checks

| Endpoint | Use |
|---|---|
| `GET /live` | Container/orchestrator liveness probe — matches `apps/backend/Dockerfile`'s own `HEALTHCHECK`. No dependency check; failure means restart the process. |
| `GET /ready` | Orchestrator readiness probe — gated on PostgreSQL. Failure means stop routing traffic here, do not restart. |
| `GET /health` | Human/dashboard-facing detailed status, including `version`, `build_commit`, `build_time`, and every datastore's individual status — see `cerebrum.api.health`. |

See [38_Observability.md](../architecture/specification/38_Observability.md)'s
Health Checks table for the full semantics behind this three-tier split.

## Connecting to Datastores

This image expects the same six datastores
[docker-architecture.md](docker-architecture.md) provisions locally,
reachable via the `POSTGRES_HOST`/`REDIS_HOST`/etc. variables — point
them at your production datastore instances (managed PostgreSQL, managed
Redis, etc.) rather than the local Compose stack. The backend connects
to all six concurrently at startup with retry and graceful degradation
(see `cerebrum.core.lifecycle`) — a temporarily-unreachable non-critical
datastore does not block startup, but `/health` reports it, and `/ready`
specifically requires PostgreSQL.

## Database Migrations

Run Alembic migrations against the target database **before** routing
traffic to a new version, from an environment with network access to
that database (a one-off job/task, not baked into the container's
`CMD`, which stays a stateless `uvicorn` process — running migrations
automatically on every container start would race under Rolling
Updates, per
[96_Deployment_Strategy.md](../architecture/specification/96_Deployment_Strategy.md)'s
backward-compatible-migration requirement):

```bash
cd apps/backend && uv run alembic upgrade head
```

## Scaling

The application is stateless (see
[80_API_Architecture.md](../architecture/specification/80_API_Architecture.md)'s
Decision Rationale) — running multiple container replicas behind a load
balancer requires no session affinity. Redis-backed rate limiting is
shared across replicas already (a Redis `INCR`, not in-process state),
so per-user/tenant/IP limits stay correct under horizontal scaling — see
`cerebrum.infrastructure.security.rate_limiter`.

## What This Guide Does Not Cover

- A specific cloud provider or Kubernetes manifests — Deferred to
  Architecture, per
  [96_Deployment_Strategy.md](../architecture/specification/96_Deployment_Strategy.md)'s
  Constraints (Open Questions 65 and 46 in
  [40_Open_Questions.md](../architecture/specification/40_Open_Questions.md)).
- A committed, reproducible `uv.lock` — see `apps/backend/Dockerfile`'s
  note; a recommended follow-up, not implemented this milestone.
- TLS termination — expected to happen at a reverse proxy/load balancer
  in front of this container, not inside it.
