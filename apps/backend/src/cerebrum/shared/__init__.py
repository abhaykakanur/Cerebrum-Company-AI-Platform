"""The shared kernel: cross-cutting types every layer may depend on
without violating the inward-dependency rule — chiefly the error
taxonomy (shared.errors), plus cross-domain utilities that are not
themselves domain logic (e.g., generic pagination helpers, common
validators, added as future domains need them).

Kept deliberately small — see
docs/architecture/specification/34_Architecture_Principles.md's
Composition over Inheritance principle. If a "shared" utility starts
encoding business rules, it belongs in a domain, not here.
"""
