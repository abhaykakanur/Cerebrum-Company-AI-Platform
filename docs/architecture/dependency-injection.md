# Dependency Injection

How Cerebrum's backend wires dependencies, and how a future phase adds a
new one — see `docs/architecture/specification/34_Architecture_Principles.md`
and CIS Phase 1 Prompt 3 Section 2's Dependency Injection requirement.

## The Container Is FastAPI's Own

Cerebrum does not build a bespoke DI container. FastAPI's `Depends()`
system, combined with `app.state`, already provides everything CIS Phase
1 Prompt 3 asks for — explicit, typed, replaceable, testable, injectable,
mockable, lifecycle-managed dependencies — without inventing a second
composition mechanism a contributor has to learn on top of FastAPI's own.
Introducing a separate DI framework here would be an unnecessary
abstraction over a solved problem.

**Service Locator is prohibited**: nothing in application code reaches
for a global registry by string key. Every dependency is declared as a
typed parameter (`Annotated[X, Depends(get_x)]`) on the function that
needs it.

## Composition Roots

Two, matching CIS Phase 1 Prompt 3 Section 2's distinction between
startup-time and request-time wiring:

| Root | Where | When it runs |
|---|---|---|
| Startup-time | `cerebrum/core/` (`factory.py`, `lifecycle.py`, `state.py`) | Once, at process start — assembles `ApplicationState` and registers everything on the FastAPI `app`. |
| Request-scoped | `cerebrum/dependencies/` | Per request — `Depends()` providers reading off `ApplicationState` or the request itself. |

## Lifetimes

FastAPI has no built-in named lifetime concept; each of the three CIS
lifetimes is achieved with a specific, documented pattern:

| Lifetime | Pattern | Examples |
|---|---|---|
| **Singleton** | Assembled once — either an `lru_cache`d function (`cerebrum.config.settings.get_settings`) or a field on `ApplicationState`, set once in `cerebrum.core.lifecycle.lifespan` and read via a `Depends()` provider in `cerebrum/dependencies/`. | Settings, Application State itself, infrastructure client placeholders (`cerebrum.dependencies.infrastructure`), Metrics/Tracer. |
| **Scoped** (per-request) | A `Depends()` provider that reads `request.state` — populated fresh by middleware on every request. | The bound request logger (`cerebrum.dependencies.logging.get_request_logger`), the `RequestContext` (`cerebrum.middleware.context`). |
| **Transient** | A plain function call with no cached state, invoked wherever needed. | `cerebrum.utils.identifiers.generate_request_id`, `cerebrum.utils.clock.utcnow`. |

## Adding a New Dependency

1. Decide its lifetime using the table above.
2. **Singleton infrastructure client** (e.g. a real PostgreSQL engine
   replacing today's `None` placeholder): construct it in
   `cerebrum.core.lifecycle.lifespan`'s startup phase, assign it to the
   matching `ApplicationState` field (already declared —
   see `cerebrum/core/state.py`), and dispose of it in the shutdown
   phase. The existing provider in `cerebrum/dependencies/infrastructure.py`
   needs no change — it already reads that field.
3. **New scoped or transient service**: add a `get_x` function to the
   relevant module under `cerebrum/dependencies/`, and an
   `XDep = Annotated[X, Depends(get_x)]` alias next to it, following the
   existing modules' pattern.
4. Never construct a service by hand inside a route or another service —
   always inject it, per this milestone's "manual service creation
   throughout the application is prohibited" rule.

## Testability

Every `Depends()` provider can be overridden per-test via FastAPI's
`app.dependency_overrides` dict — no production code changes to support
a test double. See `apps/backend/tests/conftest.py` for the pattern this
milestone's own tests use (a fresh `Settings` instance per test, rather
than overriding a dependency, since Settings is consumed as a plain
function argument to `create_application` rather than only through
`Depends`).
