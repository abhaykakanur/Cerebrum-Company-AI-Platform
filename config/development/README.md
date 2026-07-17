# Development Configuration

Per-environment configuration overrides for the **development** environment,
per `docs/architecture/specification/95_DevOps_Architecture.md`'s
Development Environments and
`docs/architecture/specification/37_Configuration_Strategy.md`'s
Configuration Precedence model (Configuration Files sit beneath
environment-variable and runtime overrides).

Empty at Repository Foundation — no environment-specific configuration
file has been needed yet; local development currently relies entirely on
`.env` (see `.env.example`). Populate this directory when a setting
needs a non-secret, version-controlled default specific to this
environment (e.g., a feature-flag baseline distinct from other
environments).
