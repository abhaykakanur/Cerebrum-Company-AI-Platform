# Connection Lifecycle

How every infrastructure client manager (`cerebrum.infrastructure.*.manager`)
acquires, retries, reports, and releases its connection. All six
managers implement the same shape —
`cerebrum.infrastructure.health.InfrastructureClientManager` — so this
document describes one lifecycle, not six.

## The Shape

```python
class SomeClientManager:
    @property
    def is_connected(self) -> bool: ...

    async def connect(self) -> None: ...      # never raises
    async def disconnect(self) -> None: ...    # idempotent
    async def health_check(self) -> ComponentHealth: ...
```

## Startup: `cerebrum.core.lifecycle.lifespan`

1. Six manager instances are constructed (cheap — no I/O) and attached
   to `ApplicationState`.
2. All six `connect()` coroutines run concurrently via `asyncio.gather`
   — a slow or down Neo4j does not delay PostgreSQL's availability.
3. Each `connect()` internally calls
   `cerebrum.infrastructure.retry.connect_with_retry`, which attempts
   the connection up to `1 + InfrastructureSettings.connect_retries`
   times, with exponential backoff starting at
   `connect_retry_backoff_seconds`.
4. **A client that never succeeds is left disconnected — this does not
   fail application startup.** The backend serves `/live` regardless;
   `/ready` and `/health` reflect which clients actually connected. See
   `docs/architecture/specification/38_Observability.md`'s Readiness
   Check definition — a down dependency should pull the process out of
   load-balancer rotation, not crash it.

## Never Leak Driver Exceptions

Every `connect()` attempt is wrapped so a failure — whatever the
underlying driver raises (`asyncpg.InvalidPasswordError`,
`redis.exceptions.TimeoutError`, `neo4j.exceptions.ServiceUnavailable`,
...) — is caught, logged with the real error message, and converted
into "this manager stays disconnected," never re-raised past
`connect_with_retry`. The one exception a caller of `.client` /
`.session_factory` *can* observe is
`cerebrum.shared.errors.exceptions.InfrastructureException`, raised
deliberately when code tries to use a manager that isn't connected —
this is intentional, immediate, actionable failure, not a leaked driver
type.

A failed attempt still allocates real resources (a partially-opened
engine, an aiohttp session) before it fails its verification call —
every manager's `connect()` closes/disposes those on failure, so a
retried attempt (or six datastores failing concurrently) never leaks a
connection pool or an open socket. See each manager's `connect()` for
the specific cleanup call (`engine.dispose()`, `client.aclose()`,
`driver.close()`, `client.close()`).

## Timeouts

Every manager honors
`cerebrum.config.infrastructure.InfrastructureSettings.connect_timeout_seconds`
via whatever mechanism its driver exposes (`connect_args={"timeout": ...}`
for asyncpg, `socket_connect_timeout` for redis-py, `connection_timeout`
for the Neo4j driver, `timeout` for Qdrant/OpenSearch). MinIO's official
SDK is synchronous and has no built-in timeout by default — its manager
configures a bounded `urllib3.PoolManager` explicitly, or an unreachable
MinIO would hang the connecting coroutine indefinitely rather than
timing out.

## Health Checks

`health_check()` is independent of `connect()`: it always performs a
fresh, lightweight liveness probe (`SELECT 1`, `PING`,
`get_collections()`, `bucket_exists()`, `verify_connectivity()`,
`ping()`) against the *current* connection, so `GET /health` reflects
the datastore's status right now, not just whether the initial startup
attempt once succeeded. A manager that was never connected (or was
disconnected) reports `"unavailable"` without attempting any I/O.

## Shutdown

`cerebrum.core.lifecycle.lifespan`'s shutdown phase calls every
manager's `disconnect()` concurrently. `disconnect()` is idempotent —
safe to call whether or not `connect()` ever succeeded — releasing
whatever pooled connections, drivers, or sessions that manager holds.

## Retry Policy

See `cerebrum.config.infrastructure.InfrastructureSettings`
(`INFRA_CONNECT_RETRIES`, `INFRA_CONNECT_RETRY_BACKOFF_SECONDS`,
`INFRA_CONNECT_TIMEOUT_SECONDS`) and
`cerebrum.infrastructure.retry.connect_with_retry` — one shared
implementation every manager's `connect()` calls, rather than six
near-identical retry loops.
