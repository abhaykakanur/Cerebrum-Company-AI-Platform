"""The PostgreSQL session dependency — "Scoped" lifetime: a fresh
``AsyncSession`` per request, unlike every other infrastructure
dependency in ``cerebrum.dependencies.infrastructure``, which is a
process-wide singleton client. See
cerebrum.infrastructure.database.session for why a SQLAlchemy session
specifically cannot be a singleton.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cerebrum.dependencies.state import ApplicationStateDep
from cerebrum.infrastructure.database.session import get_db_session as _get_db_session


async def get_db_session(state: ApplicationStateDep) -> AsyncIterator[AsyncSession]:
    async for session in _get_db_session(state.database.session_factory):
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
