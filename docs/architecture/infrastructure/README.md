# Infrastructure

The Enterprise Data & Infrastructure Foundation (CIS Phase 1, Prompt 4):
reusable connection-lifecycle management for all six of Cerebrum's
datastores, plus the Unit of Work and Repository Foundation patterns a
future domain builds on. No business queries, ORM models, or business
repositories exist yet — see each guide's own scope note.

## What Exists

| Datastore | Manager | Owns |
|---|---|---|
| PostgreSQL | `cerebrum.infrastructure.database.manager.PostgresClientManager` | Async engine, session factory, connection pool |
| Redis | `cerebrum.infrastructure.cache.manager.RedisClientManager` | Pooled async client |
| Neo4j | `cerebrum.infrastructure.graph.manager.Neo4jClientManager` | Async driver, session-per-use |
| Qdrant | `cerebrum.infrastructure.vector.manager.QdrantClientManager` | Async client |
| MinIO | `cerebrum.infrastructure.storage.manager.MinIOClientManager` | Sync client wrapped for async use, bucket validation |
| OpenSearch | `cerebrum.infrastructure.search.manager.OpenSearchClientManager` | Async client |

Every manager implements the same shape — see
[connection-lifecycle.md](connection-lifecycle.md):
`connect()` / `disconnect()` / `health_check()` / `is_connected`.

## Guides

| I want to... | Read |
|---|---|
| Understand how a connection is acquired, retried, and released | [connection-lifecycle.md](connection-lifecycle.md) |
| Understand PostgreSQL specifically (engine, sessions, pooling) | [database-architecture.md](database-architecture.md) |
| Use the Unit of Work pattern in an application service | [transaction-guide.md](transaction-guide.md) |
| Implement a concrete repository against `AbstractRepository` | [repository-guide.md](repository-guide.md) |
| Write and run an Alembic migration | [migration-guide.md](migration-guide.md) |

## Design Decisions

- **Never leak driver exceptions.** Every manager maps failures into
  `cerebrum.shared.errors.exceptions.InfrastructureException` (or its
  `ConnectionException`/`TimeoutException` subclasses) — no
  `asyncpg.*`, `redis.exceptions.*`, `neo4j.exceptions.*`, etc. type
  ever crosses a manager's public method boundary uncaught. See
  [connection-lifecycle.md](connection-lifecycle.md).
- **A failed connection never fails startup.** `cerebrum.core.lifecycle`
  connects all six clients concurrently at startup; any that fail after
  their configured retries are left disconnected, reported via
  `GET /health`, and retried again only on the next process restart —
  not polled continuously. This matches the Readiness Check semantics
  in `docs/architecture/specification/38_Observability.md`.
- **The manager owns the client; the DI layer owns access.**
  `cerebrum.core.state.ApplicationState` always holds a manager instance
  (constructed at startup, no I/O); `cerebrum.dependencies.infrastructure`
  and `cerebrum.dependencies.database` are the only two modules a route
  or future application service imports to reach an actual client.
- **PostgreSQL is the one exception to "singleton dependency."** A
  SQLAlchemy `AsyncSession` is request-scoped (see
  [database-architecture.md](database-architecture.md)); every other
  client (Redis, Neo4j, Qdrant, MinIO, OpenSearch) is handed out as the
  same process-wide singleton object, since each of those SDKs already
  manages its own internal connection pooling.
