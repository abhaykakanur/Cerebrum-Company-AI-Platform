"""The declarative base every future ORM model inherits from.

Empty of columns/mixins by design — see this package's ``__init__.py``.
Alembic's migration environment (apps/backend/alembic/env.py) imports
``Base.metadata`` as the autogenerate target, so this class's identity
(not its content) is what matters at this milestone.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every future SQLAlchemy ORM model."""
