"""PostgreSQL infrastructure: engine/session factories, the declarative
``Base``, the Unit of Work, and :class:`PostgresClientManager`.

No ORM models are defined here or anywhere else at this milestone — see
CIS Phase 1 Prompt 4's "No ORM models" scope for the Database Foundation.
:class:`~cerebrum.infrastructure.database.base.Base` exists so a future
domain's models have a declarative base to inherit from; it declares no
tables itself.
"""
