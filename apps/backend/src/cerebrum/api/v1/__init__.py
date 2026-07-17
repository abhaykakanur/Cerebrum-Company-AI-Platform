"""The versioned public API surface, ``/api/v1``.

Empty of business routes at this milestone — see this document's
Non-Objectives. Every future domain's router (Identity, Workspace,
Knowledge, ...) is included here, in cerebrum.api.v1.router, as it is
built; this package is the fixed mount point those routers attach to,
not itself a place business logic lives.
"""
