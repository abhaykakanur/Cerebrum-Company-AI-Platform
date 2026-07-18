# Security Architecture

End-to-end view of CIS Phase 1 Prompt 5 — how a request becomes an
authenticated, tenant-scoped, permission-checked action, and every
security control in the middleware pipeline.

## Request Lifecycle (Authenticated Request)

```
Trusted Host
    ↓
Security Headers            (CSP, HSTS, Cross-Origin-*, no-store on /auth/*)
    ↓
Request Size Limit          (413 if Content-Length exceeds SECURITY_MAX_REQUEST_BODY_BYTES)
    ↓
Compression
    ↓
CORS
    ↓
Request ID
    ↓
Correlation ID
    ↓
Authentication               (decodes Bearer token → request.state.auth_identity, or None)
    ↓
Request Context               (folds auth_identity + X-Workspace-ID into RequestContext)
    ↓
Request Timer
    ↓
Structured Logging
    ↓
[Exception Handler — Starlette's ExceptionMiddleware, innermost automatically]
    ↓
Router → route dependencies (CurrentUserDep / require_permission(...)) → handler
```

See `cerebrum.middleware.registry` for the exact registration mechanics
(Starlette's insert-at-front behavior means the code registers these in
the *reverse* of the order above).

## Why Authentication Runs Before Request Context

`RequestContext` is immutable once built (frozen dataclass) and carries
`tenant_id`/`authenticated_user_id`. Those can only be populated at
construction time, so whatever resolves them —
`AuthenticationMiddleware` — must run first. See
`cerebrum.middleware.context`'s and
`cerebrum.middleware.request_context`'s docstrings.

## The Middleware Exception Bypass, and How This Codebase Handles It

**Verified empirically, not assumed:** an exception raised inside a
`BaseHTTPMiddleware.dispatch()` bypasses every `@app.exception_handler`
entirely — Starlette's `ExceptionMiddleware` sits *inside* all
user-added middleware in the ASGI stack, not outside it. A middleware
that needs to reject a request (an invalid token, an oversized body)
cannot simply `raise` and rely on the standard error envelope.

Both `AuthenticationMiddleware` and `RequestSizeLimitMiddleware` instead
call `cerebrum.core.exception_handlers.build_error_response` (or, for
`AuthenticationMiddleware`, `handle_platform_exception`) **directly**,
producing the identical `ErrorResponse` envelope every other failure
path returns — the same `error_code`/`request_id`/`correlation_id`
shape, not a bespoke one. See `cerebrum.middleware.authentication`'s
docstring for the full explanation and
`apps/backend/tests/unit/test_auth_api.py::test_me_with_a_garbage_token_returns_401_with_a_populated_request_id`
for the regression test.

## Error Taxonomy

| Exception | HTTP | Category | Retryable | Raised when |
|---|---|---|---|---|
| `AuthenticationException` | 401 | Security | No | Bad credentials, no/invalid identity |
| `InvalidTokenException` | 401 | Security | No | Malformed/wrong-signature/wrong-type JWT |
| `ExpiredTokenException` | 401 | Security | No | Well-formed JWT past its `exp` |
| `AuthorizationException` | 403 | Security | No | Authenticated, but the action isn't permitted |
| `PermissionDeniedException` | 403 | Security | No | A specific RBAC check failed |
| `RateLimitExceededException` | 429 | Security | Yes (`Retry-After` header set) | Login rate limit exceeded |

All six are `PlatformException` subclasses (see
`cerebrum.shared.errors.exceptions`) and flow through the existing,
unmodified `handle_platform_exception` — no new exception-handler
registration was needed; `http_status` is read off the exception class
generically, per CIS Phase 1 Prompt 3's design.

## Configuration

Every setting lives on `cerebrum.config.security.SecuritySettings` — the
same class Phase 1 Prompt 3 created for transport security (trusted
hosts, CORS), extended rather than duplicated. See that module's
docstring for why `jwt_secret_key` is a typed `SecretStr` field (the
same interim pattern already used for `POSTGRES_PASSWORD` etc.) rather
than behind the Security Domain's not-yet-built `GetSecret` port.

| Concern | Env vars |
|---|---|
| JWT | `JWT_SIGNING_SECRET`, `SECURITY_JWT_ALGORITHM`, `SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES`, `SECURITY_REFRESH_TOKEN_EXPIRE_DAYS` |
| Password policy | `SECURITY_PASSWORD_MIN_LENGTH`, `SECURITY_PASSWORD_REQUIRE_{UPPERCASE,LOWERCASE,DIGIT,SPECIAL}` |
| Password hashing | `SECURITY_PASSWORD_HASH_{TIME_COST,MEMORY_COST_KIB,PARALLELISM}` |
| Rate limiting | `SECURITY_LOGIN_RATE_LIMIT_ATTEMPTS`, `SECURITY_LOGIN_RATE_LIMIT_WINDOW_SECONDS` |
| Sessions / API keys | `SECURITY_SESSION_IDLE_TIMEOUT_MINUTES`, `SECURITY_API_KEY_DEFAULT_EXPIRE_DAYS` |
| Transport | `SECURITY_TRUSTED_HOSTS`, `SECURITY_CORS_ALLOWED_ORIGINS`, `SECURITY_TRUSTED_PROXIES`, `SECURITY_MAX_REQUEST_BODY_BYTES` |

## Rate Limiting

`cerebrum.infrastructure.security.rate_limiter.RateLimiter` — a fixed
window counter in Redis (one `INCR` + `EXPIRE` on the window's first
hit), applied to the login endpoint only
(`cerebrum.dependencies.auth.enforce_login_rate_limit`). **Fails open**
if Redis is unreachable — logs a warning and lets the request through,
rather than making "Users can authenticate" depend on a cache being up
(consistent with CIS Phase 1 Prompt 4's graceful-degradation design for
every other infrastructure client). A `429` response carries a
`Retry-After` header (see `handle_platform_exception`'s special case for
`RateLimitExceededException`).

## Audit Trail

`cerebrum.application.auth.audit_service.AuditService` records seven
event types (`AuditEventType`: `LOGIN`, `LOGOUT`, `LOGIN_FAILED`,
`TOKEN_REFRESH`, `PERMISSION_DENIED`, `API_KEY_USED`, `SESSION_REVOKED`)
into the append-only `AuditEvent` table — `update()`/`delete()` on its
repository deliberately raise rather than silently succeeding (see
`cerebrum.repositories.postgres.audit_repository`). Audit events only —
no analytics, no aggregation.

## Known Limitations

- **No registration/password-change/password-reset endpoint** — CIS
  Phase 1 Prompt 5 asks for "foundational models only"; seeding a user
  currently requires direct repository access (see any test's
  `_auth_factories.seed_tenant_with_user`), not an API call.
- **No API key authentication path wired into the request pipeline** —
  see [api-key-guide.md](api-key-guide.md)'s Non-Objectives.
- **Request Size Limit checks `Content-Length` only** — a chunked
  request that omits it and streams past the limit is not caught; see
  `cerebrum.middleware.request_size_limit`'s docstring.
- **No migration has been applied against a real PostgreSQL instance in
  this sandbox** — see
  `docs/architecture/infrastructure/migration-guide.md` and the
  migration file's own docstring for how it was instead verified (schema
  diffed column-by-column against the SQLAlchemy models via Alembic's
  `Operations` API against a real, disposable connection).
- **No secrets backend** — `JWT_SIGNING_SECRET` is a local-development
  pattern, not production secret management; see this document's
  Configuration section.
