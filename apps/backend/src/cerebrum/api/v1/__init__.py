"""The versioned public API surface, ``/api/v1``.

Empty of *business* routes at this milestone — see this document's
Non-Objectives. ``cerebrum.api.v1.auth`` (CIS Phase 1 Prompt 5) is
platform, not business, surface: login/refresh/logout/current-user, no
product feature. Every future domain's router (Identity, Workspace,
Knowledge, ...) is included here, in cerebrum.api.v1.router, as it is
built; this package is the fixed mount point those routers attach to,
not itself a place business logic lives.
"""
