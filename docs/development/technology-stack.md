# Technology Stack

Practical reference for what's actually in this repository today. For the
architectural justification behind each choice, see
`docs/architecture/specification/32_Technology_Stack.md` and its Decision
Rationale sections, and `docs/architecture/specification/107_ADR_Catalog.md`
for the formal ADRs.

## Backend

| Component | Technology | Where |
|---|---|---|
| Language | Python 3.12+ | `apps/backend/` |
| Web framework | FastAPI | `apps/backend/pyproject.toml` |
| Validation | Pydantic v2 | same |
| Settings | pydantic-settings | same |
| Server | Uvicorn | same |
| Logging | structlog | same |
| Package manager | uv (workspace) | root `pyproject.toml` |
| Testing | Pytest | `apps/backend/tests/` |

## Frontend

| Component | Technology | Where |
|---|---|---|
| Framework | Next.js 14 (App Router) | `apps/frontend/` |
| Language | TypeScript (strict mode) | `apps/frontend/tsconfig.json` |
| Styling | Tailwind CSS | `apps/frontend/tailwind.config.ts` |
| Testing | Vitest | `apps/frontend/vitest.config.ts` |
| Package manager | pnpm (workspace) | root `pnpm-workspace.yaml` |

## Shared Packages

`@cerebrum/shared-types`, `@cerebrum/shared-config`,
`@cerebrum/shared-utils`, `@cerebrum/eslint-config`, `@cerebrum/tsconfig`
— see `packages/*/README.md` for each.

## Infrastructure (Local Development)

PostgreSQL 16, Neo4j 5 (Community + APOC), Redis 7, Qdrant, MinIO,
OpenSearch 2 — see `docs/deployment/infrastructure-overview.md` for the
full picture and `infrastructure/docker/docker-compose.yml` for the
authoritative definition.

## Not Yet Present

- No CI/CD platform is wired up yet (`.github/workflows/` contains
  placeholders only — see
  `docs/architecture/specification/97_CICD_Architecture.md` for the
  eventual 13-stage pipeline).
- No AI/LLM provider integration (`docs/architecture/specification/60_AI_Model_Abstraction.md`).
- No deployed environment — this repository currently supports local
  development only.
