"""Application layer: use cases, command/query handlers, and DTOs that
orchestrate domain objects to fulfill one CES-traceable requirement each.

See docs/architecture/specification/34_Architecture_Principles.md
(Application Layer Architecture). Depends on domain/ only, never on
infrastructure/ directly — see docs/architecture/dependency-rules.md —
with one narrow exception, established by ``application/auth/`` (CIS
Phase 1 Prompt 5): repositories are consumed through
:class:`~cerebrum.repositories.base.AbstractRepository`, the interface
Phase 1 Prompt 4 built exactly for this, but
``cerebrum.infrastructure.security``'s ``PasswordHasher``/``TokenService``
are depended on directly rather than behind a new domain-owned port.
No Identity domain exists yet to own that port (Phase 2, per
docs/architecture/specification/110_Implementation_Roadmap.md), and
introducing one now — for two stable, deterministic security
primitives unlikely to be swapped — would be exactly the kind of
premature abstraction docs/architecture/coding-guidelines.md warns
against. Every ``application/`` service still takes its dependencies via
constructor injection, never instantiating them itself.
"""
