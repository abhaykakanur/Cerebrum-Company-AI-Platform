"""Fast, deterministic secret hashing — distinct from
:mod:`cerebrum.infrastructure.security.password`'s slow, salted Argon2
hashing.

Refresh tokens and API keys are already high-entropy, randomly-generated
secrets (a JWT's signature, or ``secrets.token_urlsafe(32)``) — unlike a
user-chosen password, there is no brute-force risk a slow hash would
mitigate, and looking one up by its hash on every request needs to be
cheap. SHA-256 is standard practice for this specific case (storing a
lookup-able hash of an already-random secret), and deliberately not used
for anything password-shaped.
"""

import hashlib


def hash_secret(value: str) -> str:
    """A hex-encoded SHA-256 digest of ``value``. Used to store/look up
    refresh tokens
    (:class:`~cerebrum.infrastructure.database.models.session.UserSession.refresh_token_hash`)
    and API keys
    (:class:`~cerebrum.infrastructure.database.models.api_key.APIKey.hashed_key`)
    without ever persisting the raw secret.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
