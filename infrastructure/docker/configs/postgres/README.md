# PostgreSQL Configuration

At this milestone, PostgreSQL is configured entirely through environment
variables in `docker-compose.yml` (database name, user, password, timezone,
encoding) — no `postgresql.conf` override is mounted, since no tuning need
has yet been identified and the default configuration is appropriate for
local development.

**This directory is reserved** for a future `postgresql.conf` override
(connection limits, `shared_buffers`, `work_mem`, and similar tuning) once
Phase 3 (Knowledge Storage,
`docs/architecture/specification/110_Implementation_Roadmap.md`) or
production load-testing (`docs/architecture/specification/98_Testing_Strategy.md`)
identifies a concrete need.

See `infrastructure/docker/init/postgres/` for what runs against this
database on first container start — extension enablement only, never
application schema (per this milestone's "no schemas, no tables" scope).
