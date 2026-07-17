# Migration Guide (Alembic)

The migration framework is configured; there is nothing to migrate yet
— `cerebrum.infrastructure.database.base.Base.metadata` is empty (no ORM
model exists, per this milestone's "Do not create business tables"
scope). This guide is for the first migration a future phase adds.

## Layout

```
apps/backend/
├── alembic.ini              # Alembic config — script_location, post_write_hooks
└── alembic/
    ├── env.py                # Migration environment — reads DB URL from Settings, not alembic.ini
    ├── script.py.mako         # Revision file template
    └── versions/                # Empty — see versions/README.md for conventions
```

## Why `env.py` Reads the URL From `Settings`, Not `alembic.ini`

```python
config.set_main_option("sqlalchemy.url", get_settings().postgres.dsn)
```

`alembic.ini`'s own `sqlalchemy.url` is an unused placeholder. The real
URL comes from `cerebrum.config.settings.get_settings()` — the same
`POSTGRES_*` environment variables every other part of the backend
reads — so there is exactly one place a database connection string is
assembled, never a separately-maintained migration-only copy that could
drift from the application's actual configuration.

`alembic.ini`'s `prepend_sys_path = src` makes `import cerebrum` resolve
against this repo's src-layout package without requiring a prior
editable install.

## Running Migrations

```bash
# From apps/backend/:
uv run alembic revision --autogenerate -m "add users table"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic current
uv run alembic history
```

Every generated revision file is automatically formatted (`black`) and
linted with fixes applied (`ruff check --fix`) via `alembic.ini`'s
`[post_write_hooks]` — a generated migration never introduces a style
inconsistency a reviewer has to flag separately.

## Conventions

See `apps/backend/alembic/versions/README.md` for the full list
(one migration per schema-changing PR, always implement `downgrade()`,
read the autogenerate diff before committing it, imperative commit-style
messages). That file lives next to the migrations themselves so it's
never out of sync with the directory it documents.

## What This Milestone Does Not Do

- No business table exists — the first `alembic revision --autogenerate`
  will produce an empty migration until a future phase defines a model
  under `Base`.
- No migration has been generated or applied against a real database in
  this milestone (verified instead via a real PostgreSQL connection
  attempt through `env.py`'s full import/configuration chain, which
  reached the server and failed at authentication — not at import or
  configuration — confirming the wiring is correct up to actual
  connectivity).
