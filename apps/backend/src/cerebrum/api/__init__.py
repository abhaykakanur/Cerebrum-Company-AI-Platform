"""API layer: FastAPI routers implementing the API Domain's Public,
Internal, Administrative, and Connector API surfaces.

See docs/architecture/specification/80_API_Architecture.md and
docs/architecture/specification/81_API_Standards.md. This package contains
routing and request/response translation only — no business logic. Routers
call into `application/` use cases and return their results, per
docs/architecture/dependency-rules.md.

Empty at Repository Foundation (Phase 1, Prompt 1). No endpoints are
implemented until CES-governed feature work begins.
"""
