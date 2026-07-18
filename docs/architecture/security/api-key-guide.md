# API Key Guide

Long-lived, non-interactive credentials — the foundation a future
connector authenticates through (no connector integration exists yet;
see CIS Phase 1 Prompt 5's scope). All logic lives in
`cerebrum.application.auth.api_key_service.APIKeyService`.

## Shape

A raw key looks like `ck_<43 random URL-safe characters>` — the `ck_`
prefix (**c**erebrum **k**ey) lets a human or a secret-scanning tool
recognize it as this codebase's credential type at a glance, the same
convention GitHub/Stripe/OpenAI tokens use.

Only a SHA-256 hash of the raw key
(`cerebrum.infrastructure.security.hashing.hash_secret` — the same fast
hash `UserSession.refresh_token_hash` uses, not the slow
password-hashing Argon2 path, since an API key is already
high-entropy-random, not user-chosen) is stored in
`APIKey.hashed_key`. **The raw key is returned exactly once, at
generation** — there is no "view key again" — only rotation, which
issues a new one.

`APIKey.key_prefix` (the first several characters, cleartext) exists
purely so a list view can show "which key is this" without ever
re-displaying the secret.

## Generating a Key

```python
from cerebrum.dependencies.auth import APIKeyServiceDep

record, raw_key = await api_key_service.generate(
    user_id=current_user.id, name="CI pipeline", scopes=["read"], expires_in_days=90
)
# Surface `raw_key` to the caller now — it is never recoverable again.
```

`expires_in_days` defaults to `SECURITY_API_KEY_DEFAULT_EXPIRE_DAYS`
(365) if omitted.

## Validating a Key

```python
record = await api_key_service.validate(raw_key)
```

Raises `AuthenticationException` — the same "don't distinguish the
reason" principle as login (see
[authentication-guide.md](authentication-guide.md)) — for a key that
doesn't exist, is revoked, or has expired; a caller can't tell which.
Updates `last_used_at` as a side effect.

## Revoking and Rotating

```python
await api_key_service.revoke(record.id)              # immediate, permanent
new_record, new_raw_key = await api_key_service.rotate(record.id)  # revoke + generate, same name/scopes
```

`rotate` is what a "regenerate this key" UI action calls — the old key
stops validating the instant rotation happens, and the caller must
switch to `new_raw_key`.

## Scopes

`APIKey.scopes` is a plain `list[str]`, stored as JSON — no scope
namespace or enforcement exists yet (no connector reads it). It's
carried through generation and rotation so the shape is settled before a
consumer needs it.

## No Connector Integration Yet

Nothing in this codebase currently accepts an API key as a request
credential the way `AuthenticationMiddleware` accepts a Bearer JWT —
`APIKeyService.validate` exists and is tested
(`apps/backend/tests/unit/test_api_key_service.py`), but no middleware
or dependency wires it into the request pipeline. A future connector or
public-API milestone adds that wiring without changing this service.
