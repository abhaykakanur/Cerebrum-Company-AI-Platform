# Environment Variables Guide

## Source of Truth

`.env.example` at the repository root is the canonical, always-current
list of every environment variable this project uses. This document
explains the *categories* and *conventions*; if it and `.env.example`
ever disagree, `.env.example` is correct — update this doc to match, not
the other way around.

## Setup

```bash
cp .env.example .env
```

Then edit `.env` with real local-development values where the placeholder
(`changeme-local-only`) isn't acceptable — for infrastructure services,
the placeholder values work as-is for local development; you do not need
to change them to start the stack.

**`.env` is git-ignored and must never be committed.** See
`docs/architecture/specification/75_Security_Architecture.md`'s
Externalized Secrets Decision Rationale for why.

## Variable Categories

| Category | Examples | Notes |
|---|---|---|
| Service connection | `POSTGRES_HOST`, `NEO4J_PORT`, `QDRANT_HOST` | Where to reach each infrastructure service. |
| Service credentials | `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY` | Local-development-only values; never real credentials, never used beyond `localhost`. |
| Application config | `ENVIRONMENT`, `LOG_LEVEL`, `BACKEND_PORT` | Not yet consumed by any running code at this milestone — reserved for the application phase. |
| AI provider config | `LLM_PROVIDER`, `LLM_API_KEY` | Intentionally blank by default — no default provider is committed to by the specification (`docs/architecture/specification/40_Open_Questions.md`, Open Question 72). Leave blank unless you are specifically testing AI features once they exist. |
| Feature flags | `FEATURE_FLAGS_OVERRIDE_FILE` | Points at a local override file, per `docs/architecture/specification/37_Configuration_Strategy.md`. |

## Real Secrets vs. Local Placeholders

Every credential in `.env.example` is a clearly-marked local-only
placeholder (`changeme-local-only`). This is safe to commit precisely
because it is not a real secret — it only ever protects a Docker container
running on your own machine, reachable only from `localhost`. This is
categorically different from a staging/production secret, which is never
handled via an environment file at all — see
`docs/architecture/specification/37_Configuration_Strategy.md`'s
Configuration Precedence model and the Security Domain's `GetSecret` port.

## Adding a New Variable

1. Add it to `.env.example` with a placeholder value and a comment
   explaining what it's for and which spec document governs it.
2. Add it to the relevant table in this document.
3. If it's a new infrastructure service port, add it to
   `port-allocation.md` too.
