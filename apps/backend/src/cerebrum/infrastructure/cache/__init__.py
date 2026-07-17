"""Redis infrastructure: :class:`RedisClientManager`, the connection
lifecycle owner for the cache/session/rate-limit/Celery-broker datastore.

No cache logic (get/set wrappers, TTL policy, key naming) is implemented
here — see CIS Phase 1 Prompt 4's "No cache logic" scope. A future
domain builds cache-usage code against :attr:`RedisClientManager.client`.
"""
