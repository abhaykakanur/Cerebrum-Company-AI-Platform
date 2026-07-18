"""The Knowledge Domain's application services — CIS Phase 2 Prompt 1:
Organization/Workspace/Folder/Document/Version/Metadata/Tag/Label/
Collection. The first real *business* domain in this codebase (see
cerebrum.application's own docstring for the prior "application/auth/
only" state) — still depends on domain/ only in principle, but domain/
remains empty (no aggregates/invariants extracted yet), so these
services currently orchestrate repositories directly, matching
application/auth/'s established shape rather than inventing a domain
layer prematurely.
"""
