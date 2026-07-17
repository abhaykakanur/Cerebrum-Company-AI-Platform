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
singleton services are wired from there, and
`docs/architecture/infrastructure/` for the datastore clients themselves.

## Public Interfaces

As of the Enterprise Data & Infrastructure Foundation milestone (Phase
1, Prompt 4), the backend is a running ASGI application with a platform
surface only — no business endpoints yet. See
`docs/architecture/specification/80_API_Architecture.md` for the eventual
full API Domain surface.

| Endpoint | Purpose |
|---|---|
| `GET /live` | Liveness check — is the process running? |
| `GET /ready` | Readiness check — gated on PostgreSQL specifically (see `cerebrum.api.health`). |
| `GET /health` | Detailed per-subsystem status for all six datastores, from each client manager's live `health_check()`. |
| `GET /api/v1/` | Confirms the versioned API surface is mounted. No domain routes exist under it yet. |
| `GET /api/v1/docs`, `/api/v1/redoc` | Interactive OpenAPI docs — development/testing only, disabled in staging/production (see `cerebrum.core.metadata`). |

Every response is wrapped in the standard envelope
(`cerebrum.api.schemas.envelope`) and carries `X-Request-ID` and
`X-Correlation-ID` headers — see
`docs/architecture/specification/81_API_Standards.md`.

## Infrastructure

All six datastores (PostgreSQL, Redis, Neo4j, Qdrant, MinIO, OpenSearch)
are connected at startup with retry and graceful degradation — a client
that can't connect is reported `unavailable` via `/health`, not a
startup failure. See `docs/architecture/infrastructure/` for the full
architecture, including the Unit of Work and Repository Foundation
patterns a future domain builds on.

## Dependencies

- Python 3.12+
- FastAPI, Pydantic, structlog, uvicorn (see `pyproject.toml`)
- SQLAlchemy 2.x + asyncpg + Alembic (PostgreSQL), redis-py, the
  official Neo4j driver, qdrant-client, the official MinIO SDK,
  opensearch-py — see `docs/architecture/infrastructure/README.md`
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
`unavailable`.

## Limitations

- No database models, migrations content, authentication, authorization,
  or business API endpoints — by design; see this milestone's
  Non-Objectives in the CIS Phase 1 Prompt 4 prompt text.
  `cerebrum.infrastructure.database.base.Base` exists with no model
  registered under it; the first `alembic revision --autogenerate` is
  a no-op until one is.
- The background runtime, event dispatcher, and worker interfaces
  (`cerebrum.workers`, `cerebrum.events`) exist as contracts only — no
  concrete worker or queue implementation exists yet.
- The repository foundation (`cerebrum.repositories`) is abstract
  contracts only — no concrete repository exists yet.
- `domain/`, `application/`, and `services/` remain documentation-only
  (`__init__.py` docstrings) — they gain content starting with Phase 2
  (Identity Platform), per
  `docs/architecture/specification/110_Implementation_Roadmap.md`.
