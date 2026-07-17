# Coding Standards

This is the practical, command-level reference. For the underlying
principles and *why* each rule exists, see
`docs/architecture/coding-guidelines.md` and
`docs/architecture/specification/99_Coding_Standards.md`.

## Tooling

| Language | Formatter | Linter | Type Checker |
|---|---|---|---|
| Python | Black | Ruff | mypy (`strict = true`) |
| TypeScript | Prettier | ESLint (`@cerebrum/eslint-config`) | `tsc --noEmit` (Strict Mode) |

Run all of them: `scripts/format.sh`, `scripts/lint.sh`,
`scripts/typecheck.sh`, or all validation steps together via
`scripts/validate.sh`.

**No lint warnings are allowed to merge — this is enforced by CI, not
merely encouraged.**

## Configuration Locations

- Python tool configuration ([tool.black], [tool.ruff], [tool.isort],
  [tool.mypy], [tool.pytest.ini_options]) lives once, at the workspace
  root: `pyproject.toml`. Individual packages (`apps/backend/pyproject.toml`)
  do not repeat it.
- TypeScript tool configuration is centralized in
  `packages/eslint-config` and `packages/tsconfig`; every app/package
  extends from there rather than defining its own rules.

## General Rules (enforced in code review where tooling can't catch them)

- Meaningful names — no single-letter variables outside trivial loop
  counters, no unexplained abbreviations.
- No magic numbers — name the constant.
- Small functions, single responsibility.
- Dependency injection — no direct instantiation of an infrastructure
  adapter inside domain or application code.
- No global mutable state.
- Composition over inheritance.
- Explicit error handling — every error classified per
  `docs/architecture/specification/38_Observability.md`'s taxonomy, never
  a bare/silent `except`.

## Naming Conventions

See `docs/architecture/naming-conventions.md` for the complete, per-language
reference (Python `snake_case`/`PascalCase`/`UPPER_CASE`, TypeScript
`PascalCase` components/`camelCase` variables/`kebab-case` routes).

## Pre-Commit Hooks

Installed via `scripts/setup.sh` (or manually: `pre-commit install`).
Mirrors the fast CI checks locally — see `.pre-commit-config.yaml`.
