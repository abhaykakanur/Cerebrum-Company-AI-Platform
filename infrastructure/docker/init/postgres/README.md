# PostgreSQL Initialization

This directory is mounted to `/docker-entrypoint-initdb.d` and runs on the
**first** container start against an empty data volume only (standard
Postgres image behavior). Any `.sh` or `.sql` file placed here in a future
phase executes automatically at that point.

**Nothing is placed here yet, deliberately.** Per this milestone's binding
scope ("no schemas, no tables"), and per
`docs/architecture/specification/44_Global_Entity_Model.md`'s Global
Identifier Strategy — which specifies that entity UUIDs are generated at
the **application layer**, not via a database extension such as
`uuid-ossp` or `pgcrypto`'s `gen_random_uuid()` — this milestone does not
presume which, if any, Postgres extensions the application will need.
That is a Phase 3 (Knowledge Storage) decision, made when the actual
schema is designed, not assumed here.

This directory exists as the established extension point for that future
initialization work, per
`docs/architecture/specification/110_Implementation_Roadmap.md`.
