"""Domain layer: entities, aggregates, value objects, domain services,
domain events, and repository port interfaces for Cerebrum's 30 functional
domains.

See docs/architecture/specification/35_Domain_Architecture.md. Domain-layer
code imports nothing from application/ or infrastructure/ — see
docs/architecture/dependency-rules.md. Per-domain subpackages (identity,
workspace, knowledge, ...) are added as each domain is implemented,
starting with Phase 2 (Identity Platform) per
docs/architecture/specification/110_Implementation_Roadmap.md.
"""
