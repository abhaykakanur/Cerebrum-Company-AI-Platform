# Folder Responsibilities

One-line responsibility for every top-level and backend-layer directory.
For the full tree, see `docs/architecture/folder-structure.md`. For layer
dependency rules, see `docs/architecture/dependency-rules.md`.

## Repository Root

| Folder | Responsibility |
|---|---|
| `apps/` | Deployable applications. |
| `packages/` | Shared TypeScript libraries, consumed via workspace linking. |
| `infrastructure/` | Local infrastructure provisioning (Docker Compose). |
| `docs/` | All documentation, including the CES specification. |
| `scripts/` | The primary developer-facing command interface to this repo. |
| `config/` | Per-environment (development/testing/staging/production) configuration. |
| `tests/` | Cross-cutting, full-stack tests spanning both `apps/backend` and `apps/frontend` — app-scoped tests live inside each app instead. |
| `tools/` | Reserved for future custom developer tooling not fitting elsewhere. |
| `examples/` | Reserved for future usage examples/sample integrations. |
| `assets/` | Reserved for shared static assets not specific to the frontend app. |

## Backend Layers (`apps/backend/src/cerebrum/`)

| Folder | Responsibility |
|---|---|
| `api/` | FastAPI routers — request/response translation only, no business logic. |
| `core/` | Shared kernel: base domain types, error taxonomy, DI composition root. |
| `config/` | Environment/configuration-file loading into typed settings. |
| `domain/` | Entities, aggregates, value objects, domain services, repository port interfaces. |
| `application/` | Use cases, command/query handlers, DTOs — orchestrates domain objects. |
| `infrastructure/` | Adapters implementing domain/application port interfaces against real technology. |
| `shared/` | Cross-domain utilities that are not pure, dependency-free helpers (see `utils/`) but also aren't domain logic. |
| `services/` | Cross-domain application services composing multiple domains (e.g., Administration). |
| `workers/` | Background Processing Layer: the nine named Workers and their Task/Workflow definitions. |
| `repositories/` | Concrete repository adapters, one subpackage per datastore technology. |
| `events/` | Domain event definitions and in-process dispatch. |
| `middleware/` | ASGI middleware: authentication, tenant-scoping, tracing — applied once, centrally. |
| `dependencies/` | FastAPI dependency-injection providers (request-scoped composition). |
| `utils/` | Small, generic, dependency-free helpers with zero domain awareness. |

## Frontend (`apps/frontend/`)

| Folder | Responsibility |
|---|---|
| `app/` | Next.js App Router pages and layouts. |
| `components/` | The Design System component catalog — every page builds from here exclusively. |
| `features/` | Feature-specific components/logic, composed from `components/`. |
| `hooks/` | Shared, feature-agnostic React hooks. |
| `layouts/` | Layout System primitives (nav, sidebar, command palette, ...). |
| `lib/` | The typed API client. |
| `providers/` | React context providers. |
| `services/` | Request-orchestration wrappers around `lib/`, consumed by `features/`. |
| `styles/` | Global styling not expressible as Tailwind utilities/tokens. |
| `types/` | Frontend-local TypeScript types (cross-cutting types live in `packages/shared-types`). |
| `utils/` | Small, generic, dependency-free helpers. |
| `public/` | Static assets served as-is. |
