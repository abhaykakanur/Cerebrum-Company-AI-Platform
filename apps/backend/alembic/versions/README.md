# Migration Versions

Empty — no ORM model exists yet (see CIS Phase 1 Prompt 4's "Do not
create business tables" scope), so there is nothing to migrate. The
first migration is generated once a future phase defines a model under
`cerebrum.infrastructure.database.base.Base`.

## Conventions

- One migration per PR that changes the schema. Do not bundle unrelated
  schema changes into a single revision.
- Autogenerate first (`alembic revision --autogenerate -m "..."`), then
  read the generated diff before committing it — autogenerate detects
  column/table changes but not data migrations, renames (it sees a
  rename as a drop+add), or check constraints in every dialect.
- Every migration must be reversible: implement `downgrade()`, not just
  `upgrade()`. A migration with `pass` in `downgrade()` is rejected in
  review unless the change is genuinely one-way (documented why in the
  migration's docstring).
- Message format: an imperative summary of the schema change (e.g.
  `"add users table"`, `"add index on documents.workspace_id"`), not a
  restatement of the ticket/PR number.

See `docs/architecture/infrastructure/migration-guide.md` for the full
workflow.
