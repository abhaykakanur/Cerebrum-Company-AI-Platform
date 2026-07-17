<!--
Every element below is required per
docs/architecture/specification/97_CICD_Architecture.md's Code Review
section and CONTRIBUTING.md. A PR missing any of these is not ready for
review.
-->

## Description

<!-- What changed and why, in human terms. -->

## Linked Requirement

<!--
A Requirement ID from docs/architecture/specification/22_Requirement_Catalog.md,
or the specific non-functional CES document driving this change. A change
with no traceable requirement is a signal it may be out of scope — see
CONTRIBUTING.md.
-->

## Linked ADR (if applicable)

<!-- Link to the ADR if this implements or is governed by one. -->

## Testing Evidence

<!--
What did you run, and what was the result? Reference specific test
files/commands (scripts/test.sh, scripts/validate.sh output, etc.).
-->

## Screenshots (UI changes only)

<!-- Before/after screenshots for any Frontend Layer change. Delete this section if not applicable. -->

## Review Checklist

- [ ] Follows `docs/architecture/dependency-rules.md` (no reverse/circular dependencies, no feature coupling).
- [ ] Follows `docs/architecture/naming-conventions.md`.
- [ ] No lint warnings (`scripts/lint.sh` passes clean).
- [ ] Type checks pass (`scripts/typecheck.sh`).
- [ ] Tests added/updated for the change; `scripts/test.sh` passes.
- [ ] Documentation updated if this changes public interfaces, folder structure, or developer workflow.
- [ ] No secrets, credentials, or `.env` values committed.
- [ ] No undocumented technical debt introduced (see `docs/architecture/specification/109_Project_Governance.md` if a shortcut was necessary).

## Approval

<!-- Reviewer: check this once you've verified the above and approve. -->
- [ ] Approved
