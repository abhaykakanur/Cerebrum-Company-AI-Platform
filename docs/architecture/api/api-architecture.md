# API Architecture

Elaborates docs/architecture/specification/80_API_Architecture.md and
docs/architecture/specification/81_API_Standards.md for this codebase
specifically — what exists today, not a restatement of the specs
themselves.

## Router Framework

One top-level router (`cerebrum.api.router.router`) aggregates every
sub-router; `cerebrum.core.routers.register_routers` mounts exactly that
one router onto the application — no other module calls
`app.include_router`. Today it aggregates three:

```
cerebrum.api.router.router
├── cerebrum.api.health.router          # unversioned: /live, /ready, /health
├── cerebrum.api.version_routes.router  # unversioned: /api/versions
└── cerebrum.api.v1.router.router       # /api/v1, tags=["API v1"]
    └── cerebrum.api.v1.auth.router     # /api/v1/auth, tags=["Authentication"]
```

A future domain router (Identity, Workspace, Knowledge, ...) is included
in `cerebrum.api.v1.router`, following `auth_router`'s exact pattern:

```python
from fastapi import APIRouter
from cerebrum.api.openapi_responses import STANDARD_ERROR_RESPONSES

router = APIRouter(prefix="/documents", tags=["Documents"], responses=STANDARD_ERROR_RESPONSES)
```

## Why Health and Versions Are Unversioned

`/live`, `/ready`, `/health`, and `/api/versions` are mounted outside
`/api/v1` deliberately — see `cerebrum.api.health`'s docstring and CIS
Phase 1 Prompt 3 Section 3's API Foundation list, which names these
alongside, not beneath, `/api/v1`. A process-orchestration signal
(health) or version-discovery endpoint must be reachable before a client
has committed to a specific API version.

## URL Conventions

Resource-oriented, plural, no verbs in paths — see
[80_API_Architecture.md](../specification/80_API_Architecture.md)'s URL
Conventions. `cerebrum.api.v1.auth`'s login/refresh/logout/me is the one
deliberate near-exception (verb-shaped by OAuth2 Password Flow
convention, not this codebase's choice) — see that module's docstring.

## Stateless

No server-side session state is required to interpret a request beyond
the access token itself — see
[76_Authentication_Architecture.md](../specification/76_Authentication_Architecture.md).
`UserSession` rows (CIS Phase 1 Prompt 5) exist for revocation/audit, not
as authentication state a request depends on.
