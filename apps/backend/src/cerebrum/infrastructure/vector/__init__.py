"""Qdrant infrastructure: :class:`QdrantClientManager`, the connection
lifecycle owner for the authoritative vector datastore.

No vector operations (collection creation, upserts, similarity search)
are implemented here — see CIS Phase 1 Prompt 4's "No vector operations"
scope.
"""
