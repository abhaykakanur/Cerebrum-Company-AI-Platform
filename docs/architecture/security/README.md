# Identity & Security

The Identity, Security & Multi-Tenancy Foundation (CIS Phase 1, Prompt
5): JWT authentication, password hashing, RBAC, API keys, session
tracking, multi-tenancy context, and the security middleware pipeline.
Reusable platform only — no business permissions, no user-facing
registration/profile flow, no connector integration. See each guide's
own scope note for specifics.

## Guides

| I want to... | Read |
|---|---|
| Understand login/refresh/logout and token lifecycle | [authentication-guide.md](authentication-guide.md) |
| Protect a route with a permission check | [rbac-guide.md](rbac-guide.md) |
| Understand how tenant/workspace context resolves | [multi-tenancy-guide.md](multi-tenancy-guide.md) |
| Generate/validate/rotate an API key | [api-key-guide.md](api-key-guide.md) |
| See the whole security architecture end to end | [security-architecture.md](security-architecture.md) |

## What Exists

| Concern | Where |
|---|---|
| ORM models (User, Organization, Workspace, Role, Permission, WorkspaceMembership, APIKey, UserSession, AuditEvent) | `cerebrum.infrastructure.database.models` |
| Password hashing (Argon2id) | `cerebrum.infrastructure.security.password` |
| JWT issuance/validation | `cerebrum.infrastructure.security.jwt` |
| Fast secret hashing (refresh tokens, API keys) | `cerebrum.infrastructure.security.hashing` |
| Rate limiting | `cerebrum.infrastructure.security.rate_limiter` |
| Concrete repositories | `cerebrum.repositories.postgres.*` |
| Application services | `cerebrum.application.auth.*` |
| Authentication middleware | `cerebrum.middleware.authentication` |
| Current-user / RBAC dependencies | `cerebrum.dependencies.auth` |
| HTTP surface | `cerebrum.api.v1.auth` (`/api/v1/auth/login`, `/refresh`, `/logout`, `/me`) |

## Non-Objectives

Explicitly out of scope for this milestone — see the CIS Phase 1 Prompt
5 prompt text: knowledge ingestion, AI, RAG, search, knowledge graph,
connectors, chat, document processing, business workflows, analytics,
memory. No business permission code (e.g. `"documents:read"`) is seeded
anywhere in this codebase — every example in these guides using one is
illustrative, for a future domain to actually define.
