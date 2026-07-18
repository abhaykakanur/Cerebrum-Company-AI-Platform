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
- `test_password_hashing.py`, `test_jwt.py`, `test_authentication_service.py`,
  `test_authorization_service.py`, `test_api_key_service.py`,
  `test_sessions.py`, `test_tenant_isolation.py`, `test_rate_limiter.py`,
  `test_auth_api.py` — Argon2 password hashing, JWT issuance/validation,
  login/refresh/logout (against the same in-memory SQLite pattern),
  RBAC permission checks, API key generation/validation/rotation,
  session tracking, cross-tenant isolation, rate limiting (against a
  fake in-memory Redis — see `test_rate_limiter.py`'s docstring), and
  the full HTTP surface through the real middleware pipeline (Phase 1,
  Prompt 5). `_auth_factories.py` is shared test-data-seeding helpers,
  not a test module itself (no `test_` prefix — not collected).
- `test_query_params.py`, `test_response_builder.py`, `test_api_versions.py`,
  `test_request_context_dependencies.py`, `test_file_foundation.py`,
  `test_rate_limit_dependencies.py`, `test_openapi.py`,
  `test_metrics_middleware.py` — the API platform layer: pagination/
  filtering/sorting query-param parsing, response-envelope building, the
  API Version Registry (both the registry itself and `GET /api/versions`),
  Tenant/Request ID/Correlation ID/Permissions dependencies (against a
  throwaway mounted route, following `test_auth_api.py`'s
  `TestRoutePermissionProtection` precedent), File Foundation validation,
  the completed Per User/Tenant/API Key/Anonymous rate limiter (against
  the same fake-Redis pattern as `test_rate_limiter.py`), OpenAPI tag/
  operation-ID/error-documentation generation, and API metrics recording
  (against an in-memory `MetricsRegistry` swapped in for the real
  no-op) (Phase 1, Prompt 6).
- `test_event_dispatcher.py`, `test_infrastructure_dependencies.py`,
  `test_request_logger_dependency.py`, `test_logging_redaction.py` —
  Production Readiness's test-coverage improvement: real, working code
  (the in-process event dispatcher, the infrastructure DI providers, the
  request-scoped logger provider, the structlog redaction processor)
  that had zero direct coverage despite no concrete business use consuming
  it yet — see each module's own docstring for why untested-but-real
  code is worth covering regardless. `test_metrics_middleware.py` gained
  tracing-span coverage (a `_RecordingTracer` fake, mirroring the
  existing `_RecordingMetricsRegistry` one) alongside its existing
  metrics coverage. `test_configuration.py` gained coverage for the new
  production-secret-placeholder rejection and JWT algorithm allowlist.
  `test_authentication_service.py` gained a regression test
  (`test_login_does_not_block_the_event_loop`) proving the Argon2
  blocking-call fix below actually holds (Phase 1, Prompt 7).
