"""Identity & Security infrastructure (CIS Phase 1 Prompt 5): password
hashing (:mod:`cerebrum.infrastructure.security.password`) and JWT
issuance/validation (:mod:`cerebrum.infrastructure.security.jwt`).

These wrap third-party security libraries (argon2-cffi, PyJWT) the same
way cerebrum.infrastructure's other subpackages wrap their respective
client SDKs — see docs/architecture/dependency-rules.md's "infrastructure/
is the only layer permitted to import third-party infrastructure SDKs."
No route, service, or repository imports ``argon2``/``jwt`` directly;
everything goes through
:class:`~cerebrum.infrastructure.security.password.PasswordHasher` or
:class:`~cerebrum.infrastructure.security.jwt.TokenService`.
"""
