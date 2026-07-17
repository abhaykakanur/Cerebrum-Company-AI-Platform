# Database Architecture (PostgreSQL)

PostgreSQL is Cerebrum's authoritative relational datastore — see
`docs/architecture/specification/42_Database_Responsibilities.md`. This
document covers the platform-level engine/session/pooling architecture
built in CIS Phase 1 Prompt 4. **No ORM model exists yet** — this is
foundation a future domain's models are built on, not a schema.

## Layers

```
cerebrum.config.database.PostgresSettings      # typed config, POSTGRES_* env vars, .dsn
        ↓
cerebrum.infrastructure.database.engine         # create_engine(dsn, **kwargs) -> AsyncEngine
        ↓
cerebrum.infrastructure.database.manager.PostgresClientManager
        ↓ (owns)
    AsyncEngine  +  async_sessionmaker[AsyncSession]
        ↓
cerebrum.infrastructure.database.session.get_db_session   # per-request AsyncSession
cerebrum.infrastructure.database.unit_of_work.UnitOfWork   # explicit transaction boundary
```

## Why `engine.py` Takes a Raw DSN, Not `PostgresSettings`

`create_engine()` is dialect-agnostic on purpose — it accepts a DSN
string and passthrough keyword arguments, not a
`PostgresSettings` object. `PostgresClientManager` is what supplies
PostgreSQL-specific pool tuning (`pool_size`, `max_overflow`,
`pool_recycle`, `pool_pre_ping`). This split is what lets
`apps/backend/tests/unit/test_unit_of_work.py` point the same factory at
an in-memory SQLite database to test transaction mechanics without a
real PostgreSQL instance — see that test module's docstring.

## Connection Pooling

`PostgresClientManager.connect()` builds the engine with:

| Setting | Value | Why |
|---|---|---|
| `pool_pre_ping` | `True` | Validates a pooled connection with a lightweight ping before handing it out — a connection dropped by the server (idle timeout, restart) is detected and replaced instead of surfacing as a confusing mid-query failure. |
| `pool_size` | 5 | Baseline pooled connections per process. |
| `max_overflow` | 10 | Additional connections allowed under burst load, closed once idle. |
| `pool_recycle` | 1800s | Connections older than this are recycled — guards against a database server or intermediate proxy silently closing long-idle connections. |

Connection success is verified once at `connect()` time with a
lightweight `SELECT 1` (SQLAlchemy's async engine is otherwise lazy —
it would not actually attempt a connection until first use, which would
make "all infrastructure clients initialize" unverifiable at startup).

## Sessions Are Request-Scoped, Never Singleton

Unlike every other infrastructure client (Redis, Neo4j, Qdrant, MinIO,
OpenSearch — see `cerebrum.dependencies.infrastructure`, all singleton),
a SQLAlchemy `AsyncSession` tracks an in-progress unit of work and must
never be shared across concurrent requests. `cerebrum.dependencies.database.DbSessionDep`
yields a fresh session per request via
`cerebrum.infrastructure.database.session.get_db_session`, which commits
on a clean exit and rolls back on any exception — never leaking the
underlying `SQLAlchemyError` past that boundary (mapped to
`InfrastructureException`).

For multi-step operations an application service controls explicitly
(rather than the implicit per-request commit above), see
[transaction-guide.md](transaction-guide.md)'s Unit of Work.

## Health

`PostgresClientManager.health_check()` runs a fresh `SELECT 1` against a
short-lived connection on every call — independent of whether the
initial `connect()` succeeded — so `GET /health` always reflects current
reachability. See [connection-lifecycle.md](connection-lifecycle.md).
