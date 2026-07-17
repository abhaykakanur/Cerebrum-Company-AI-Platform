"""The Unit of Work pattern: an explicit, reusable transaction boundary
an application service controls directly, as an alternative to the
implicit per-request commit of
:func:`~cerebrum.infrastructure.database.session.get_db_session`.

No repository is wired in here — see CIS Phase 1 Prompt 4's "No
repositories yet" scope. A future application service composes a
:class:`UnitOfWork` with one or more repositories (see
cerebrum.repositories) built against ``unit_of_work.session``.
"""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cerebrum.shared.errors.exceptions import InfrastructureException


class UnitOfWork:
    """One transaction's lifecycle: begin, do work against
    :attr:`session`, then exactly one of commit or rollback, always
    followed by dispose.

    Usable as an async context manager (commits on clean exit, rolls
    back on exception, always disposes) or driven explicitly via
    :meth:`begin`/:meth:`commit`/:meth:`rollback`/:meth:`dispose` for
    call sites that need finer control than a ``with`` block allows.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise InfrastructureException(
                "UnitOfWork has no active session — call begin() or enter it "
                "as an async context manager first."
            )
        return self._session

    async def begin(self) -> None:
        self._session = self._session_factory()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def dispose(self) -> None:
        """Idempotent — safe to call even if :meth:`begin` was never
        called, or :meth:`dispose` was already called once.
        """
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "UnitOfWork":
        await self.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            await self.dispose()
