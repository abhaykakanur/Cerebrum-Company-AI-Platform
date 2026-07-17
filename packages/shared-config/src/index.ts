/**
 * @cerebrum/shared-config — public entry point.
 *
 * For NON-SECRET, shared runtime configuration constants only (e.g.,
 * feature-flag key names, well-known route paths, shared enum-like
 * constants). NEVER for secrets — see
 * docs/architecture/specification/37_Configuration_Strategy.md and
 * docs/architecture/specification/75_Security_Architecture.md's
 * Externalized Secrets Decision Rationale. A secret value committed to
 * this package would defeat that architecture entirely, since this
 * package is version-controlled and bundled into the frontend.
 *
 * Empty at Repository Foundation — no configuration constants are shared
 * across packages yet.
 */

export {};
