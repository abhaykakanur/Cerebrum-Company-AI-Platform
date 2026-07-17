# Contributing to Cerebrum

Cerebrum is built against a single source of truth: the Cerebrum Engineering
Specification (CES), located at
[`docs/architecture/specification/`](docs/architecture/specification/README.md).
Every contribution is expected to conform to it. This guide explains how to
get set up and how changes are made and reviewed.

## Before You Start

1. Read [docs/development/getting-started.md](docs/development/getting-started.md)
   to get your environment running.
2. Read [docs/architecture/repository-architecture.md](docs/architecture/repository-architecture.md)
   and [docs/architecture/dependency-rules.md](docs/architecture/dependency-rules.md)
   — these define non-negotiable structural rules enforced in code review.
3. If your change touches product behavior, find its governing requirement in
   [docs/architecture/specification/22_Requirement_Catalog.md](docs/architecture/specification/22_Requirement_Catalog.md).
   A change with no traceable requirement is a signal the work may be out of
   scope for this specification — raise it for discussion before writing code.

## The CES Is Authoritative

This repository implements the CES; it does not redesign it. If your work
requires deviating from the CES — a different technology, a simplified
architecture, a new pattern — that is an architectural decision, not an
implementation detail, and requires an ADR
(see `docs/architecture/specification/09_Governance.md` and
`docs/architecture/specification/107_ADR_Catalog.md`) reviewed and accepted
by the Architecture Owner **before** the code is written, not after.

## Development Workflow

1. **Branch** from `develop` (or `main` for a `hotfix/*`), following the
   branch strategy in
   `docs/architecture/specification/97_CICD_Architecture.md`:
   `feature/*`, `bugfix/*`, `hotfix/*`, `release/*`.
2. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, ...), per the
   same document's Decision Rationale for why this convention is required.
3. **Test** locally — `pnpm test` / `uv run pytest` per
   [docs/development/development-guide.md](docs/development/development-guide.md).
4. **Open a pull request** against `develop`, including every element
   required by `docs/architecture/specification/97_CICD_Architecture.md`'s
   Code Review section:
   - Description
   - Linked Requirement (a Requirement ID, or the specific non-functional
     document driving the change)
   - Linked ADR, if applicable
   - Testing Evidence
   - Screenshots, for any frontend change
   - A completed Review Checklist
5. **Address review feedback** and obtain Approval before merge.

## Coding Standards

Every contribution must pass, without warnings:

- **Python:** Black, Ruff, isort, mypy (strict)
- **TypeScript:** ESLint, Prettier, `tsc --strict`

See [docs/development/coding-standards.md](docs/development/coding-standards.md)
for the full standard, and
`docs/architecture/specification/99_Coding_Standards.md` for its full
architectural justification.

**No lint warnings are allowed to merge.** This is a binding rule, not a
guideline — see [docs/architecture/specification/99_Coding_Standards.md](docs/architecture/specification/99_Coding_Standards.md).

## No Undocumented Technical Debt

If you must take a shortcut, it must be logged as a tracked technical debt
item (Description, Reason, Impact, Owner, Priority, Removal Plan, Deadline)
per `docs/architecture/specification/109_Project_Governance.md`, not left
undocumented in the code.

## Code of Conduct

Participation in this project is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Questions

If a requirement is ambiguous, check
[`docs/architecture/specification/114_Open_Questions.md`](docs/architecture/specification/114_Open_Questions.md)
— it may already be a tracked, known ambiguity. If it is not, raise it rather
than resolving it by assumption; this specification's own governing
principle throughout is "record ambiguity, do not invent architecture."
