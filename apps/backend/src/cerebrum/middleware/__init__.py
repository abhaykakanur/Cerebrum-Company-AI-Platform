"""ASGI/FastAPI middleware: authentication verification, tenant-scoping,
correlation ID propagation, and request tracing — applied once, centrally,
ahead of every request reaching a router.

See docs/architecture/specification/30_System_Architecture.md's Security
Overview ("Authentication is enforced once, centrally, in the
Authentication Layer's request middleware") and
docs/architecture/specification/81_API_Standards.md's Request Standards.
"""
