# 37 — Configuration Strategy

## Purpose

This document defines the architecture for how Cerebrum is configured across environment variables, configuration files, secrets, feature flags, and runtime configuration. It elaborates the Configuration Layer and Security Domain's secrets-management placement from [30_System_Architecture.md](30_System_Architecture.md) and the Configuration Domain's architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Scope

This document covers configuration architecture and the boundaries between its four categories. It does not cover the Configuration Domain's business-facing requirements (AI/search configuration, feature flags) in detail — see FR-CG-001 through FR-CG-004 in [20_Functional_Requirements.md](20_Functional_Requirements.md) — or specific secret values, which never appear in any CES document.

## Definitions

- **Environment Variable** — A process-level configuration value, typically deployment-topology-specific (e.g., database host).
- **Configuration File** — A version-controlled file defining structural, non-secret defaults (e.g., default retention period).
- **Secret** — Any credential, key, or token whose disclosure would compromise security; never version-controlled, never logged.
- **Feature Flag** — A runtime-toggleable boolean or multi-value setting controlling capability availability without a deployment.
- **Runtime Configuration** — Configuration that can change without a process restart, read fresh (or from a short-lived cache) on each use.

## The Four Configuration Categories

### 1. Environment Variables

**Use:** Deployment-topology-specific values that differ between local, staging, and production environments but are not secret in themselves (e.g., `DATABASE_HOST`, `LOG_LEVEL`, `ENVIRONMENT_NAME`).

**Architecture:** Read once at process startup into a validated Pydantic Settings object (per [32_Technology_Stack.md](32_Technology_Stack.md)), injected via the Dependency Injection container ([34_Architecture_Principles.md](34_Architecture_Principles.md)) — never read ad hoc via `os.environ` scattered through domain or application code. A `.env.example` file (see [33_Directory_Structure.md](33_Directory_Structure.md)) documents every required variable with a placeholder, non-functional value.

**Ownership:** Infrastructure Layer (startup composition), not the Configuration Domain — environment variables configure the deployment, not product behavior.

### 2. Configuration Files

**Use:** Structural, non-secret defaults that are the same across environments but benefit from being externalized from code (e.g., `logging.yaml`'s log format, `feature_flags.default.yaml`'s baseline flag states before any organization-level override).

**Architecture:** Version-controlled, loaded at startup alongside environment variables, and layered *beneath* both environment-variable overrides and Configuration Domain runtime overrides — i.e., a configuration file defines the lowest-priority default, not a hard-coded value.

**Ownership:** Infrastructure Layer (loading mechanism); file content is authored by whichever team owns the setting's default (e.g., the Security Domain owns default password-policy values).

### 3. Secrets

**Use:** Connector credentials (FR-CN-001), LLM/embedding provider API keys, database credentials, JWT signing keys, encryption keys.

**Architecture:** Secrets are NEVER stored in environment variables directly in production, NEVER committed to configuration files, and NEVER logged (enforced by the Structlog adapter's field-redaction configuration, see [38_Observability.md](38_Observability.md)). Secrets are retrieved exclusively through the Security Domain's `GetSecret` port ([35_Domain_Architecture.md](35_Domain_Architecture.md)), whose Infrastructure Layer adapter targets a dedicated secrets-management backend (Deferred to Architecture for the specific product — e.g., a cloud provider's secrets manager or HashiCorp Vault). Local development MAY use an environment-variable-backed `GetSecret` adapter implementation for convenience, provided it cannot be selected in a staging/production deployment configuration (enforced by environment-gated dependency injection at startup).

**Ownership:** Security Domain.

### 4. Feature Flags and Runtime Configuration

**Use:** AI configuration (FR-CG-001), search configuration (FR-CG-002), feature flags (FR-CG-003), and other system settings (FR-CG-004) that must be changeable by an authorized administrator without a deployment, per FR-CG-001's "changes take effect for subsequent queries without a restart."

**Architecture:** Owned by the Configuration Domain, persisted in PostgreSQL (via the Persistence Layer), read through the `ConfigurationApplicationService.getConfig` port with organization/workspace-scoped inheritance resolution (FR-OR-003), and aggressively cached in Redis given the read-heavy, low-churn access pattern this data has (read on nearly every request; written only via explicit administrative action). Cache invalidation occurs synchronously on write (`setConfig` invalidates the affected key's cache entry immediately), never relying on TTL expiry alone for correctness-sensitive settings like AI grounding strictness.

**Ownership:** Configuration Domain.

## Configuration Precedence

For any given setting with multiple possible sources, precedence is (highest to lowest):

1. Workspace-level Configuration Domain override
2. Organization-level Configuration Domain default (FR-OR-003 inheritance)
3. Configuration file baseline default
4. Hard-coded application default (used only if no configuration source defines the value — treated as a gap to be filled, not a permanent state, per Explicit Dependencies in [34_Architecture_Principles.md](34_Architecture_Principles.md))

Environment variables and secrets do not participate in this precedence chain — they configure the deployment/process, not product-level, organization-scoped behavior, and therefore have no "organization override."

## Responsibilities

- Every new configurable behavior introduced in a later phase must be classified into exactly one of the four categories above at design time, not left ambiguous.
- Any code found reading a secret from anywhere other than the Security Domain's `GetSecret` port is a security-review-blocking finding, not a style issue.

## Constraints

- This document does not name the specific secrets-management product used in production — Deferred to Architecture, tracked as an open question if unresolved (see [40_Open_Questions.md](40_Open_Questions.md)).
- No default value, threshold, or specific setting name is prescribed here — this document defines the configuration *mechanism*, not its content.

## Future Considerations

- As Configuration Domain read volume grows, the caching strategy may need a dedicated invalidation-propagation mechanism across multiple backend process instances (relevant once the modular monolith is horizontally scaled per [39_Performance_Targets.md](39_Performance_Targets.md)) — Deferred to Architecture.

## Acceptance Criteria

- [ ] All four configuration categories from the governing specification (environment variables, configuration files, secrets, feature flags/runtime configuration) are addressed with a clear architectural boundary.
- [ ] Secrets handling is explicitly connected to the Security Domain and never described as living in environment variables in production.
- [ ] A precedence order is defined for settings with multiple possible sources.
