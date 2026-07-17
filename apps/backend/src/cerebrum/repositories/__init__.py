"""The repository foundation: abstract contracts (``base.py``,
``contracts.py``, ``soft_delete.py``) every future concrete repository
implements, plus — once a domain exists — concrete repository adapter
implementations satisfying domain-owned Repository port interfaces (see
domain/), one subpackage per datastore technology.

See docs/architecture/specification/42_Database_Responsibilities.md.
Structurally, the concrete-implementation half of this package is a
specialization of infrastructure/ broken out for navigability given how
many domains define a repository port. No concrete business repository
exists yet — see CIS Phase 1 Prompt 4's "No concrete business
repositories" scope.
"""
