# Unit Tests (Backend)

Fast, isolated tests with all external dependencies mocked — see
`docs/architecture/specification/98_Testing_Strategy.md`'s Unit Testing
section. Every business rule (domain entity invariant, domain service,
application use case) gets one here.

No business-rule tests exist yet — no business rules exist yet (see
`apps/backend/README.md`'s Limitations). The tests currently in this
directory instead prove the platform foundation's own acceptance
criteria, since that platform code is itself now real and testable:

- `test_health.py`, `test_configuration.py`, `test_exceptions.py`,
  `test_middleware.py` — application startup, the middleware pipeline,
  configuration validation, and the exception framework (Phase 1,
  Prompt 3).
- `test_retry.py`, `test_unit_of_work.py`, `test_repository_contracts.py`,
  `test_infrastructure_managers.py` — the connection-retry policy, the
  Unit of Work's transaction semantics (against an in-memory SQLite
  database — see `test_unit_of_work.py`'s docstring), the repository
  foundation's pagination/filtering/sorting/soft-delete contracts, and
  every infrastructure client manager's connection lifecycle (Phase 1,
  Prompt 4). None of these require real infrastructure — see
  `docs/architecture/infrastructure/connection-lifecycle.md`.
