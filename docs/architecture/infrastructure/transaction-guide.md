# Transaction Guide (Unit of Work)

Two ways application code touches a PostgreSQL transaction. Pick based
on how much control the call site needs — neither is "deprecated" by
the other.

## 1. Implicit — `DbSessionDep` (most route handlers)

```python
from cerebrum.dependencies.database import DbSessionDep

@router.get("/something")
async def handler(session: DbSessionDep) -> SomethingResponse:
    result = await session.execute(...)
    ...
    # No explicit commit — cerebrum.infrastructure.database.session.get_db_session
    # commits automatically when the request completes without raising,
    # and rolls back automatically if it does.
```

One session, one implicit transaction, scoped exactly to the request.
Correct for the common case: a single logical operation per request.

## 2. Explicit — `UnitOfWork` (multi-step application services)

For an application service that needs to perform several distinct steps
— possibly touching several future repositories — as one atomic
transaction, with explicit control over exactly when it commits:

```python
from cerebrum.infrastructure.database.unit_of_work import UnitOfWork

async def some_application_service(uow_factory: Callable[[], UnitOfWork]) -> None:
    async with uow_factory() as uow:
        # uow.session is a real AsyncSession — pass it to any repository
        # built against cerebrum.repositories.base.AbstractRepository.
        ...
        # Commits automatically on clean exit; rolls back and re-raises
        # on any exception. Always disposes (closes the session) either way.
```

Or driven explicitly, when a `with` block doesn't fit the call site's
control flow:

```python
uow = manager.create_unit_of_work()   # PostgresClientManager.create_unit_of_work()
await uow.begin()
try:
    ...
    await uow.commit()
except Exception:
    await uow.rollback()
    raise
finally:
    await uow.dispose()
```

## Why Both Exist

`get_db_session`'s implicit per-request commit is the simplest thing
that works for a single-operation route handler — no boilerplate,
correct by default. `UnitOfWork` exists for the case that pattern
doesn't fit: an application service (not yet built — see this
milestone's Non-Objectives) composing multiple repository calls into one
transaction, independent of the HTTP request/response cycle that
triggered it (e.g., a background Task in a future phase).

## Rules

- Never hold a `UnitOfWork` or session open across an `await` that calls
  out to another service/datastore unrelated to the transaction — it
  holds a real pooled connection for its entire lifetime.
- Never share one session/`UnitOfWork` across concurrent tasks. Each is
  single-use, single-transaction.
- A repository (see [repository-guide.md](repository-guide.md)) never
  commits or rolls back itself — that's the `UnitOfWork`'s (or
  `get_db_session`'s) responsibility. A repository only reads/writes
  through the session it was constructed with.
