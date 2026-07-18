# Cerebrum Backend

The Modular Monolith backend implementing all 30 CES functional domains.
See `docs/architecture/specification/30_System_Architecture.md` for the
full architecture this package realizes.

## Architecture Overview

This package follows Clean/Hexagonal Architecture
(`docs/architecture/specification/34_Architecture_Principles.md`): each
top-level directory under `src/cerebrum/` is one layer, with dependencies
pointing strictly inward. See `docs/architecture/dependency-rules.md` for
the enforced rule set and `docs/architecture/layer-responsibilities.md`
for what belongs in each layer.

`cerebrum.main` loads configuration and delegates to
`cerebrum.core.factory.create_application`, the Application Factory —
the only place the FastAPI app is assembled. It registers, in order: the
middleware pipeline (`cerebrum.middleware.registry`), the centralized
exception handlers (`cerebrum.core.exception_handlers`), routers
(`cerebrum.core.routers`), OpenAPI customization
(`cerebrum.core.openapi`), and the (currently no-op) background runtime
(`cerebrum.core.background`). `cerebrum.core.lifecycle.lifespan` owns the
async startup/shutdown sequence, including connecting all six
infrastructure clients — see
`docs/architecture/dependency-injection.md` for how request-scoped and
singleton services are wired from there,
`docs/architecture/infrastructure/` for the datastore clients,
`docs/architecture/security/` for authentication/RBAC/multi-tenancy, and
`docs/architecture/api/` for the reusable API platform layer.

## Public Interfaces

As of the Production Readiness & Platform Hardening milestone (Phase 1,
Prompt 7 — Phase 1's final milestone), the backend is a running ASGI
application with a platform surface only — no business endpoints yet.
See `docs/architecture/specification/80_API_Architecture.md` for the
eventual full API Domain surface.

| Endpoint | Purpose |
|---|---|
| `GET /live` | Liveness check — is the process running? Matches `apps/backend/Dockerfile`'s container `HEALTHCHECK`. |
| `GET /ready` | Readiness check — gated on PostgreSQL specifically (see `cerebrum.api.health`). |
| `GET /health` | Detailed per-subsystem status for all six datastores, plus `version`/`build_commit`/`build_time` (see `cerebrum.config.application.ApplicationSettings`). |
| `GET /api/versions` | The API Version Registry — every major version this backend serves and its lifecycle status (see `cerebrum.api.versions`). |
| `GET /api/v1/` | Confirms the versioned API surface is mounted. No domain routes exist under it yet. |
| `POST /api/v1/auth/login` | OAuth2 Password Flow login — returns an access/refresh token pair. |
| `POST /api/v1/auth/refresh` | Rotates a refresh token for a new pair. |
| `POST /api/v1/auth/logout` | Revokes a refresh token's session. |
| `GET /api/v1/auth/me` | The authenticated caller's user record. |
| `GET /api/v1/docs`, `/api/v1/redoc` | Interactive OpenAPI docs (with the OAuth2 "Authorize" flow wired to `/api/v1/auth/login`, tag descriptions, tag-scoped operation IDs, and standard error-response documentation) — development/testing only, disabled in staging/production (see `cerebrum.core.metadata`). |

Every response is wrapped in the standard envelope
(`cerebrum.api.schemas.envelope`, built by `cerebrum.api.response_builder`)
and carries `X-Request-ID` and `X-Correlation-ID` headers — see
`docs/architecture/specification/81_API_Standards.md`. The `/api/v1/auth/*`
and health/version endpoints are the exceptions (see
`cerebrum.api.schemas.auth`'s docstring): `TokenResponse` is the flat
OAuth2 shape Swagger UI's "Authorize" popup requires, not the generic
envelope.

## Infrastructure

All six datastores (PostgreSQL, Redis, Neo4j, Qdrant, MinIO, OpenSearch)
are connected at startup with retry and graceful degradation — a client
that can't connect is reported `unavailable` via `/health`, not a
startup failure. See `docs/architecture/infrastructure/` for the full
architecture, including the Unit of Work and Repository Foundation
patterns.

## Identity & Security

JWT authentication (access + refresh tokens, with rotation), Argon2
password hashing, an RBAC framework, API keys, session tracking, and
tenant-scoped request context — see `docs/architecture/security/` for
the full architecture. Ten ORM models
(`cerebrum.infrastructure.database.models`: `Organization`, `Workspace`,
`User`, `Role`, `Permission`, `RolePermission`, `WorkspaceMembership`,
`APIKey`, `UserSession`, `AuditEvent`) with one Alembic migration.

## API Platform

Reusable platform infrastructure every future feature router builds on
— see `docs/architecture/api/` for the full guide set:

- **Pagination/Filtering/Sorting**: `cerebrum.dependencies.pagination`
  translates query strings into `cerebrum.repositories.contracts`'s
  datastore-agnostic contracts (`?page=`/`?page_size=`, `?sort=`,
  `?filter=field:operator:value`).
- **Response standardization**: `cerebrum.api.response_builder` fills
  the standard envelope's request-scoped fields automatically.
- **API Version Registry**: `cerebrum.api.versions` — `GET /api/versions`.
- **OpenAPI**: tag descriptions, tag-scoped operation IDs
  (`cerebrum.core.metadata`), and standard error-response documentation
  on every `/api/v1` route (`cerebrum.api.openapi_responses`).
- **Request Context dependencies**: Tenant, Request ID, Correlation ID,
  and Permissions (`cerebrum.dependencies.request_context`), alongside
  Current User/Workspace from Phase 1, Prompt 5.
- **File Foundation**: reusable upload/download/streaming/validation
  interfaces (`cerebrum.infrastructure.storage.files`) — no concrete
  adapter or ingestion feature yet.
- **General-purpose rate limiting**: Per User/Tenant/API Key/Anonymous
  dependency factories (`cerebrum.dependencies.rate_limit`), completing
  the login-specific limiter from Phase 1, Prompt 5.
- **API metrics and tracing**: Latency/Request Count/Status
  Codes/Endpoint Usage/Response Size hooks through the `MetricsRegistry`
  port, and one span per request through the `Tracer` port
  (`cerebrum.middleware.metrics`) — still no-op pending a real backend.

## Production Hardening (Phase 1, Prompt 7)

- **Enforced production configuration safety**: the process refuses to
  start in `staging`/`production` with a wildcard trusted-host/CORS
  policy, an unrotated default datastore credential, or an unsafe
  `SECURITY_JWT_ALGORITHM` (e.g. `"none"`) — see
  `cerebrum.config.settings.Settings` and
  `docs/deployment/production-deployment.md`.
- **Production Docker image**: `apps/backend/Dockerfile` — multi-stage,
  non-root, with a container-native `HEALTHCHECK` against `/live`. See
  `docs/deployment/production-deployment.md`.
- **CI pipeline**: `.github/workflows/ci.yml` — formatting, linting,
  `mypy --strict`, unit tests with coverage, secret/dependency scanning,
  and Docker build verification on every push/PR.
- **Performance**: Argon2 password verification/hashing now runs via
  `asyncio.to_thread` in `cerebrum.application.auth.authentication_service`
  rather than blocking the event loop — a login previously stalled every
  other concurrent request on the same process for the duration of one
  password check.
- **Logging safety**: the structlog redaction processor
  (`cerebrum.core.logging`) now matches sensitive field names by
  substring, not exact match, catching e.g. `hashed_password` or
  `raw_api_key` under the same `password`/`api_key` denylist entries.
- Architecture verified programmatically: no circular imports, no
  cross-layer import violations, no duplicate abstractions (three
  near-identical client-IP-resolution helpers were consolidated into
  `cerebrum.middleware.context.get_client_ip`).

## Dependencies

- Python 3.12+
- FastAPI, Pydantic, structlog, uvicorn (see `pyproject.toml`)
- SQLAlchemy 2.x + asyncpg + Alembic (PostgreSQL), redis-py, the
  official Neo4j driver, qdrant-client, the official MinIO SDK,
  opensearch-py — see `docs/architecture/infrastructure/README.md`
- PyJWT, argon2-cffi, python-multipart, email-validator — see
  `docs/architecture/security/README.md`
- Managed via [uv](https://docs.astral.sh/uv/) as a workspace member of
  the repository root's `pyproject.toml`

## Configuration

Typed, validated, environment-driven — see `cerebrum.config.settings.Settings`
and `docs/architecture/specification/37_Configuration_Strategy.md`. Every
variable is documented in `.env.example` at the repository root.
Application code never reads `os.environ` directly.

## Usage

```bash
# From the repository root:
uv sync
uv run uvicorn cerebrum.main:app --reload   # or: uv run cerebrum
uv run pytest apps/backend/tests -m unit

# Database migrations (from apps/backend/):
uv run alembic upgrade head
```

With the server running, `curl http://localhost:8000/health` returns the
detailed health envelope — start local infrastructure first
(`scripts/start.sh`) for every datastore to report `healthy` instead of
`unavailable`, and run the migration above so `/api/v1/auth/login` has
tables to query against.

### Docker

```bash
# From the repository root:
docker build -f apps/backend/Dockerfile -t cerebrum-backend .
docker run -p 8000:8000 --env-file .env cerebrum-backend
```

See `docs/deployment/production-deployment.md` for the full build/run/
deploy guide, including required production configuration changes.

## Limitations

- No registration/password-change/password-reset endpoint, and no
  business API endpoints — by design; see this milestone's
  Non-Objectives in the CIS Phase 1 Prompt 5 prompt text. Seeding a user
  requires direct repository access (see
  `apps/backend/tests/unit/_auth_factories.py`), not an API call.
- No API key authentication path is wired into the request pipeline yet
  — see `docs/architecture/security/api-key-guide.md`'s Non-Objectives.
- The File Foundation (`cerebrum.infrastructure.storage.files`) defines
  interfaces only — no concrete MinIO-backed adapter and no
  upload/download route exist yet. The general-purpose rate limiter's
  Per Workspace dimension (the fifth of five in
  `81_API_Standards.md`) is similarly deferred to the first
  workspace-scoped route that needs it.
- The background runtime, event dispatcher, and worker interfaces
  (`cerebrum.workers`, `cerebrum.events`) exist as contracts only — no
  concrete worker or queue implementation exists yet.
- `domain/` and `services/` remain documentation-only (`__init__.py`
  docstrings); `application/` holds only `application/auth/` (platform,
  not a business use case) — a business domain gains content starting
  with Phase 2 (Identity Platform), per
  `docs/architecture/specification/110_Implementation_Roadmap.md`.
- No migration has been applied against a real PostgreSQL instance in
  this development sandbox — see
  `docs/architecture/security/security-architecture.md`'s Known
  Limitations for how it was instead verified.
- No `uv.lock` is committed yet — `apps/backend/Dockerfile` re-resolves
  dependencies on every build rather than installing a pinned,
  reproducible set. See that Dockerfile's header comment.
- `apps/backend/Dockerfile` and `.github/workflows/ci.yml` were written
  and reviewed carefully but **not executed** in this development
  sandbox (no `docker`/`uv` CLI available here) — verify a real
  `docker build` and a CI run on the actual GitHub Actions runners
  before relying on either in a real deployment.
- CI (`.github/workflows/ci.yml`) covers the backend only — the
  frontend's `pnpm lint`/`typecheck`/`test` scripts are not wired into
  CI yet, since `apps/frontend/` remains placeholder scaffolding with
  nothing meaningful to check (see `docs/architecture/folder-structure.md`).
  Wiring it in is a recommended follow-up once real frontend
  implementation begins.
