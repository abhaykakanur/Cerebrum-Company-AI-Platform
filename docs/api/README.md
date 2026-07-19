# API Documentation

The API Domain (`apps/backend/src/cerebrum/api/`) implements 130+ routes
across 21 domain modules under `apps/backend/src/cerebrum/api/v1/`,
mounted at `/api/v1` (plus `apps/backend/src/cerebrum/api/health.py` and
`version_routes.py` at the application root). See
`docs/architecture/specification/80_API_Architecture.md` through
`docs/architecture/specification/83_Webhook_Architecture.md` for the
architecture this surface implements.

## Live Reference

FastAPI generates an OpenAPI schema from the route definitions
automatically — do not hand-maintain a static copy of it here, since it
would drift from the actual code. With the backend running:

| URL                 | What                   |
| ------------------- | ---------------------- |
| `GET /docs`         | Interactive Swagger UI |
| `GET /redoc`        | ReDoc reference        |
| `GET /openapi.json` | Raw OpenAPI 3 schema   |

## Response Envelope

Every route except `cerebrum.api.v1.auth` (OAuth2 Password Flow
convention) and `cerebrum.api.health` (orchestrator convention) returns:

```jsonc
// Success
{
  "success": true,
  "message": string | null,
  "data": T,
  "metadata": object | null,
  "pagination": { "page", "page_size", "total_items", "total_pages", "has_next", "has_previous", "cursor" } | null,
  "timestamp": string,
  "request_id": string,
  "correlation_id": string | null,
  "version": string
}

// Error
{
  "success": false,
  "error_code": string,
  "message": string,
  "details": [{ "field": string | null, "message": string }] | null,
  "documentation_url": string | null,
  "retryable": boolean,
  "timestamp": string,
  "request_id": string,
  "correlation_id": string | null,
  "version": string
}
```

See `apps/backend/src/cerebrum/api/schemas/envelope.py` for the exact
Pydantic models and `apps/frontend/lib/api/client.ts` for a complete,
typed consumer of this contract (the frontend's one HTTP chokepoint —
every domain-specific client module in `apps/frontend/lib/api/` is a
thin, typed wrapper around it).

## Authentication

`POST /auth/login` is `application/x-www-form-urlencoded`
(`OAuth2PasswordRequestForm`, field name `username` for email) and
returns an **unwrapped** `TokenResponse`. `POST /auth/refresh` takes JSON
`{refresh_token}`; `POST /auth/logout` takes JSON `{refresh_token}` and
returns 204; `GET /auth/me` returns an unwrapped `CurrentUserResponse`.
There is no registration route — accounts are provisioned out-of-band.

Every workspace-scoped route requires an `X-Workspace-ID` header;
organization-level routes (e.g. listing workspaces, `GET/PATCH
/organizations/me`) derive the organization solely from the JWT and
require no such header. See
`docs/architecture/security/security-architecture.md`.

## Domain Index

| Prefix                                                                           | Domain                                                            | Module                                                                                       |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `/auth`                                                                          | Login, refresh, logout, current user                              | `auth.py`                                                                                    |
| `/organizations`                                                                 | Organization settings                                             | `organizations.py`                                                                           |
| `/workspaces`                                                                    | Workspace CRUD                                                    | `workspaces.py`                                                                              |
| `/folders`, `/documents`, `/tags`, `/labels`, `/collections`, `/processing-jobs` | Document management, versions, chunks, processing pipeline        | `folders.py`, `documents.py`, `tags.py`, `labels.py`, `collections.py`, `processing_jobs.py` |
| `/entities`, `/relationships`, `/graph`                                          | Knowledge graph                                                   | `entities.py`, `relationships.py`, `knowledge_graph.py`                                      |
| `/search`                                                                        | Semantic/hybrid search                                            | `semantic.py`                                                                                |
| `/retrieval`                                                                     | Multi-strategy retrieval, RAG context assembly, explainability    | `retrieval.py`                                                                               |
| `/ai`                                                                            | RAG question answering (incl. SSE streaming), AI usage statistics | `ai.py`                                                                                      |
| `/conversations`                                                                 | AI Chat conversations and messages (incl. SSE streaming)          | `conversations.py`                                                                           |
| `/connectors`                                                                    | Source system connectors, sync runs                               | `connectors.py`                                                                              |
| `/workflows`                                                                     | Workflow automation, execution, scheduling                        | `workflows.py`                                                                               |
| `/capsules`                                                                      | Employee Knowledge Capsules, organizational risk analysis         | `capsules.py`                                                                                |

Every one of these has a corresponding typed client module in
`apps/frontend/lib/api/` — that pairing is the fastest way to see a
concrete request/response example for any given endpoint, since the
frontend was built directly against this real, running API rather than
against the idealized architecture docs.

## What Doesn't Exist Yet

No `/users`, `/roles`, or `/audit-log` endpoints — RBAC/audit logging
happens internally (permission checks, audit event writes) but is not
itself exposed as a queryable API surface. No Search Session persistence
endpoint. No message-feedback-capture endpoint. Do not assume these
exist when building against this API; the frontend's "Known Limitations"
section (`apps/frontend/README.md`) documents every UI feature that was
scoped down or omitted because of a gap like this.
