# Authentication Guide

JWT authentication: access tokens, refresh tokens with rotation,
password hashing, and the login/refresh/logout/current-user HTTP
surface. No registration endpoint exists — see this guide's Non-Objectives.

## Tokens

| | Access Token | Refresh Token |
|---|---|---|
| Lifetime | `SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES` (default 15 min) | `SECURITY_REFRESH_TOKEN_EXPIRE_DAYS` (default 30 days) |
| Carries | `sub` (user id), `org_id` (tenant), `type`, `jti`, `iat`, `exp` | same shape, `type="refresh"` |
| Presented as | `Authorization: Bearer <token>` header | Request body (`refresh_token` field) |
| Tracked server-side? | No — stateless, verified by signature alone | Yes — one `UserSession` row per issued refresh token (see [multi-tenancy-guide.md](multi-tenancy-guide.md) for why `org_id`, not `workspace_id`, is embedded) |

Signed with `SECURITY_JWT_ALGORITHM` (default `HS256`) and
`JWT_SIGNING_SECRET` — see
`cerebrum.infrastructure.security.jwt.TokenService` and
[security-architecture.md](security-architecture.md) for why that secret
is a typed `Settings` field rather than behind the not-yet-built
Security Domain `GetSecret` port.

## Login

```
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=alice@example.com&password=CorrectHorse123!
```

OAuth2 Password Flow: the form field is `username` regardless of what
the identifier actually is (email, here) — that's the spec's naming,
not this codebase's. Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Rate-limited per client IP (`SECURITY_LOGIN_RATE_LIMIT_ATTEMPTS` per
`SECURITY_LOGIN_RATE_LIMIT_WINDOW_SECONDS`) — see
[security-architecture.md](security-architecture.md)'s Rate Limiting
section. Both "no such user" and "wrong password" return the identical
401 message (no user enumeration) — see
`cerebrum.application.auth.authentication_service`'s
`_GENERIC_LOGIN_FAILURE_MESSAGE`.

## Using the Access Token

```
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

Any route depending on `cerebrum.dependencies.auth.CurrentUserDep` (the
"Current User Dependency") requires this header; a route depending on
`OptionalCurrentUserDep` works with or without it — see CIS Phase 1
Prompt 5's "Anonymous requests where allowed."

## Refresh — Token Rotation

```
POST /api/v1/auth/refresh
Content-Type: application/json

{"refresh_token": "..."}
```

Every refresh **revokes the presented token and issues a brand-new
pair** — the old refresh token stops working the instant a new one is
issued, not just when it expires. A stolen-and-reused refresh token is
detectable this way: the legitimate client's next refresh attempt fails
because its token was already rotated by the attacker's use, a strong
signal something is wrong. See
`cerebrum.application.auth.authentication_service.AuthenticationService.refresh`.

## Logout

```
POST /api/v1/auth/logout
Content-Type: application/json

{"refresh_token": "..."}
```

Revokes the session (`UserSession.revoked_at`). Idempotent — logging out
an already-revoked or unrecognized token succeeds silently.

## Password Hashing

Argon2id (`cerebrum.infrastructure.security.password.PasswordHasher`),
not bcrypt — no 72-byte truncation footgun, current OWASP first
recommendation. Cost parameters
(`SECURITY_PASSWORD_HASH_TIME_COST`/`_MEMORY_COST_KIB`/`_PARALLELISM`)
are configurable; `PasswordHasher.needs_rehash()` detects a stored hash
produced under different parameters, and
`AuthenticationService.login` transparently re-hashes on the next
successful login — no forced password reset needed after an operator
raises the cost factor.

## Password Policy

`cerebrum.infrastructure.security.password.validate_password_policy` —
configurable minimum length and character-class requirements
(`SECURITY_PASSWORD_MIN_LENGTH`, `SECURITY_PASSWORD_REQUIRE_*`). Not
wired into any endpoint yet (no registration/password-change endpoint
exists) — it's available for the domain that adds one.

## Secure Cookies (Future-Ready)

`SECURITY_USE_SECURE_COOKIES` exists on `SecuritySettings` but is not
yet wired into any response — no frontend consumes a cookie-based
refresh flow at this milestone. The JSON body (both tokens) is the only
mechanism today; a future phase can add `Set-Cookie` for the refresh
token without changing the token issuance/rotation logic itself.
