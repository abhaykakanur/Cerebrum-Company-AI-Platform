"""Cross-cutting utilities shared across domains that are not themselves
domain logic (e.g., generic pagination helpers, common validators).

Kept deliberately small — see docs/architecture/specification/34_Architecture_Principles.md's
Composition over Inheritance principle. If a "shared" utility starts
encoding business rules, it belongs in a domain, not here.
"""
