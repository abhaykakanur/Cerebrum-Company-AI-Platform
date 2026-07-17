# Infrastructure Overview

## What This Covers

The local infrastructure stack provisioned by
`infrastructure/docker/docker-compose.yml`: the six datastores of
Cerebrum's Canonical Storage Model. It does not cover application
deployment (the backend/frontend containers), which is introduced in a
later implementation phase — this milestone is infrastructure only.

## The Six Services

| Service | Role | Spec Reference |
|---|---|---|
| PostgreSQL | Authoritative relational datastore | `docs/architecture/specification/41_Data_Architecture.md` |
| Neo4j | Authoritative relationship (graph) datastore | same |
| Qdrant | Authoritative vector datastore | same |
| Redis | Cache, sessions, rate limits, Celery broker | same |
| MinIO | Authoritative binary object storage (S3-API-compatible) | same |
| OpenSearch | Keyword/hybrid search engine | `docs/architecture/specification/32_Technology_Stack.md` |

Each service has exactly one responsibility, per
`docs/architecture/specification/41_Data_Architecture.md`'s Data
Architecture Principle 13 ("every storage technology shall have one clear
responsibility") — see `service-responsibilities.md` for the full
per-service detail and what each is explicitly forbidden from owning.

## Design Intent

This infrastructure is built to be:

- **Deterministic and repeatable** — every developer who runs
  `scripts/start.sh` gets an identical environment, defined entirely by
  version-controlled configuration, never by manual setup steps.
- **Production-inspired, not production-hardened** — the same six
  services, the same container images, and (mostly) the same
  configuration shape a production deployment would use, but with
  development-appropriate defaults (disabled security plugins, permissive
  local credentials) explicitly called out wherever they diverge. See
  `troubleshooting.md` for what MUST change before any non-local use.
- **Independently configurable** — every service's port, credentials, and
  resource sizing are environment-variable-driven (see
  `environment-variables.md`), never hardcoded into the compose file.

## Where Things Live

```
infrastructure/docker/
├── docker-compose.yml       # The single source of truth for the stack
├── configs/                 # Per-service configuration overrides (or a
│                             # README explaining why none is needed yet)
├── init/                    # First-boot initialization (bucket creation, etc.)
└── healthchecks/            # Host-side aggregate health check script
```

See `docker-architecture.md` for why the compose file is organized this
way, and `local-development.md` for the day-to-day commands.

## Quick Start

```bash
cp .env.example .env   # only needed once
scripts/start.sh
scripts/doctor.sh
```

See `local-development.md` for the complete command reference.
