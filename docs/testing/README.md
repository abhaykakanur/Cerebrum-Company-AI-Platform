# Testing Guide

As of CIS Phase 1 Prompt 7, 246 backend unit tests exist under
`apps/backend/tests/unit/` — see
`docs/architecture/specification/98_Testing_Strategy.md` for the
complete nine-layer Testing Pyramid this project follows long-term; this
document covers what's actually written today and how to write more.

## Running Tests

```bash
# From the repository root:
uv run pytest apps/backend/tests -m unit          # fast, default (scripts/test.sh)
uv run pytest apps/backend/tests -m unit --cov=cerebrum --cov-report=term-missing
scripts/test.sh --all                              # unit + integration + e2e (needs infra running)
```

CI (`.github/workflows/ci.yml`) runs the unit suite with coverage on
every push/PR and uploads the coverage report as a build artifact.

## What Exists

Only `apps/backend/tests/unit/` is populated — `integration/`, `e2e/`,
`performance/`, and `ai_evaluation/` remain structural placeholders (see
each directory's own `README.md`), since no business feature exists yet
to write those test types against. See
`apps/backend/tests/unit/README.md` for the full, current list of what
each test module proves and which CIS prompt introduced it — that
document is kept up to date as the authoritative index; this guide
covers *how* to test, not an enumeration that would immediately drift.

## Test Markers

```python
pytestmark = pytest.mark.unit
```

Every test module declares exactly one marker at module level (see root
`pyproject.toml`'s `[tool.pytest.ini_options]` for the full list: `unit`,
`integration`, `e2e`, `performance`, `ai_evaluation`). `-m unit` is what
CI and `scripts/test.sh` (without `--all`) run by default — fast,
fully-isolated, no real infrastructure required.

## Patterns Established in This Codebase

### In-Memory SQLite Instead of Real PostgreSQL

`apps/backend/tests/conftest.py`'s `db_session`/`db_client` fixtures use
an in-memory SQLite database (`StaticPool`, schema created from
`Base.metadata`) rather than a real PostgreSQL connection — acceptable
because these tests exercise SQLAlchemy's own query-building and this
codebase's repository/service logic, not PostgreSQL-specific SQL
dialect behavior. A test that specifically needs PostgreSQL semantics
belongs in `integration/`, not `unit/`, once that suite exists.

### Fake Infrastructure Clients Over Mocking Frameworks

See `test_rate_limiter.py`'s `_FakeRedis` and
`test_rate_limit_dependencies.py`'s equivalent: a minimal, hand-written
class implementing only the specific methods under test, rather than
`unittest.mock.Mock`/`MagicMock`. This catches a caller passing the
wrong arguments (a `Mock` silently accepts anything) and reads as
executable documentation of exactly what the real client contract is.

### Throwaway Routes for Dependency-Only Features

`test_auth_api.py::TestRoutePermissionProtection` and
`test_request_context_dependencies.py` mount a route that exists only
for the test, proving a FastAPI dependency (`require_permission`,
`TenantIdDep`, ...) works end-to-end over HTTP when no real business
route uses it yet. Follow this pattern for any new platform-level
dependency: prove it through the real middleware pipeline, not just as
an isolated unit.

### Direct Unit Tests of "Private" Helpers

Test files import and call underscore-prefixed module functions directly
(e.g. `test_logging_redaction.py` imports
`cerebrum.core.logging._redact_sensitive_fields`,
`test_middleware.py` calls `middleware._resolve_client_ip`) rather than
only testing through a public entry point. Acceptable in this codebase
specifically because these are small, pure, single-module helpers where
testing "publicly" would mean an indirect, harder-to-diagnose test —
this is not a license to reach into arbitrary internals of a class with
real encapsulated state.

### Regression Tests for Concurrency/Performance Properties

`test_authentication_service.py::test_login_does_not_block_the_event_loop`
proves a non-functional property (the event loop stays responsive during
password verification) by racing a trivial concurrent coroutine against
the call under test — see that test's docstring for the empirically
verified failure mode it guards against. Write this style of test when
fixing a blocking-call bug, not as a general pattern for every async
function.

## Coverage

`pytest-cov` (already a dev dependency) generates the report CI uploads.
Locally:

```bash
uv run pytest apps/backend/tests -m unit --cov=cerebrum --cov-report=html
open htmlcov/index.html   # or your platform's equivalent
```

100% coverage is not a goal in itself. `cerebrum.workers.queue`/`scheduler`
(abstract interfaces with no concrete implementation yet — see their own
docstrings) and `cerebrum.main` (the ASGI entrypoint, exercised by
actually starting the process, not a unit test) are expected to show low
or zero coverage; this is a correct reflection of what these modules are,
not a gap to close artificially.

## Writing a New Test

1. One test module per source module under test, named `test_<module>.py`.
2. `pytestmark = pytest.mark.unit` at module level.
3. A module-level docstring stating which acceptance criterion or CIS
   prompt the tests prove — see any existing test file for the pattern.
4. Prefer the fake-object pattern above over mocking-framework mocks for
   anything beyond a single trivial return value.
5. Run `scripts/validate.sh` before opening a PR.
