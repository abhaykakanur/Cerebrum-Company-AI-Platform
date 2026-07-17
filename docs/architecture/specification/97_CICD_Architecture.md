# 97 — CI/CD Architecture

## Purpose

This document defines the thirteen-stage CI/CD pipeline, the Git branching strategy and Conventional Commits standard, and the seven-element Code Review requirement governing every change to Cerebrum's codebase.

## Scope

This document covers pipeline stages, version control workflow, and code review process. It does not cover the specific tools implementing each pipeline stage in depth beyond naming them (see [99_Coding_Standards.md](99_Coding_Standards.md) for the specific linting/formatting tools) or testing methodology (see [98_Testing_Strategy.md](98_Testing_Strategy.md), which the pipeline's Unit/Integration Tests stages invoke). No CI/CD configuration file content (YAML, pipeline scripts) appears in this document.

## Definitions

- **Conventional Commits** — A commit message convention (`type(scope): description`) that makes commit history machine-parseable for changelog generation and semantic versioning inference.
- **Build Verification** — Confirming the codebase compiles/builds successfully, distinct from and prerequisite to running tests against that build.

## CI/CD Pipeline

The pipeline SHALL include the following thirteen stages, executed in order, with a failure at any stage blocking progression to the next:

| # | Stage | Purpose |
|---|---|---|
| 1 | Static Analysis | Detects code-quality issues beyond simple formatting (complexity, unused code, common bug patterns). |
| 2 | Formatting | Verifies code matches the canonical format per [99_Coding_Standards.md](99_Coding_Standards.md)'s tooling (Black, Prettier). |
| 3 | Linting | Verifies style and correctness rules per [99_Coding_Standards.md](99_Coding_Standards.md)'s tooling (Ruff, ESLint). |
| 4 | Type Checking | Verifies strong typing per [99_Coding_Standards.md](99_Coding_Standards.md) (mypy, TypeScript Strict Mode). |
| 5 | Dependency Validation | Confirms declared dependencies are consistent, resolvable, and free of known-vulnerable versions (overlapping with, but distinct in timing from, the later Security Scanning stage's deeper vulnerability analysis). |
| 6 | Unit Tests | Per [98_Testing_Strategy.md](98_Testing_Strategy.md)'s Unit Testing section. |
| 7 | Integration Tests | Per [98_Testing_Strategy.md](98_Testing_Strategy.md)'s Integration Testing section. |
| 8 | Security Scanning | Dependency Scans, Secret Detection, Static Analysis (security-focused), per [98_Testing_Strategy.md](98_Testing_Strategy.md)'s Security Testing section and [79_Threat_Model.md](79_Threat_Model.md). |
| 9 | Build Verification | See definition above. |
| 10 | Artifact Generation | Produces the deployable container images per [95_DevOps_Architecture.md](95_DevOps_Architecture.md)'s Docker Strategy. |
| 11 | Deployment Approval | A human or automated gate (Deferred to Architecture for which, per environment) before Staging/Production deployment proceeds. |
| 12 | Deployment | Per [96_Deployment_Strategy.md](96_Deployment_Strategy.md)'s applicable model for the target environment. |
| 13 | Post-Deployment Validation | Automated smoke tests and health-check verification confirming the newly deployed version is actually serving traffic correctly, per [38_Observability.md](38_Observability.md)'s Readiness checks. |

Stages 1–5 (static checks) execute fastest and fail fastest, giving developers the quickest possible feedback loop, consistent with Developer Productivity from this Part's Objective. End-to-End, Performance, and AI Evaluation tests ([98_Testing_Strategy.md](98_Testing_Strategy.md)) are not included in every pipeline run by default — Deferred to Architecture for their specific triggering cadence (every merge to `main` vs. a scheduled/nightly run), given their higher cost and longer execution time relative to Unit/Integration Tests.

### Decision Rationale: Why CI/CD Automation

CI/CD automation is mandatory, not optional tooling, because it is the only mechanism by which the extensive standards established across this entire CES — Engineering Principles ([95_DevOps_Architecture.md](95_DevOps_Architecture.md)), Coding Standards ([99_Coding_Standards.md](99_Coding_Standards.md)), the Testing Strategy ([98_Testing_Strategy.md](98_Testing_Strategy.md)), and Security requirements ([75_Security_Architecture.md](75_Security_Architecture.md), [79_Threat_Model.md](79_Threat_Model.md)) — can be verified consistently on every change, rather than relying on individual developer discipline or manual review to catch every violation. This directly extends the "no quick fixes become permanent architecture" rule from [95_DevOps_Architecture.md](95_DevOps_Architecture.md): an automated pipeline is what makes that rule enforceable at scale rather than aspirational.

## Version Control

**Git SHALL be used.** Branch Strategy:

| Branch | Purpose |
|---|---|
| `main` | Always deployable; represents the current Production-equivalent state. |
| `develop` | Integration branch for features awaiting release. |
| `feature/*` | Individual feature development, branched from and merged back into `develop`. |
| `bugfix/*` | Non-urgent bug fixes, following the same flow as `feature/*`. |
| `hotfix/*` | Urgent production fixes, branched from `main` and merged into both `main` and `develop`. |
| `release/*` | Release stabilization/preparation, branched from `develop`, merged into `main` on release. |

**Commit messages SHALL follow Conventional Commits** (see definition above).

### Decision Rationale: Why Conventional Commits

Conventional Commits is adopted because it makes commit history machine-parseable, enabling automated changelog generation and providing the structured signal (`feat`/`fix`/`BREAKING CHANGE` prefixes) that could inform automated semantic version bumps for [80_API_Architecture.md](80_API_Architecture.md)'s Major/Minor version distinction — connecting the human act of committing code to the API Versioning discipline already established, rather than requiring a separate, manually maintained changelog process prone to drifting out of sync with actual changes.

## Code Review

Every pull request SHALL include: Description, Linked Requirement, Linked ADR (if applicable), Testing Evidence, Screenshots (UI), Review Checklist, Approval.

| Element | Purpose |
|---|---|
| Description | What changed and why, in human terms. |
| Linked Requirement | Traceability back to a Requirement ID from [22_Requirement_Catalog.md](22_Requirement_Catalog.md), or the specific Part 8/9 document driving a non-functional change. |
| Linked ADR (if applicable) | Where the change reflects or resolves an Architecture Decision Record per [09_Governance.md](09_Governance.md). |
| Testing Evidence | Confirmation the relevant [98_Testing_Strategy.md](98_Testing_Strategy.md) test types were run and passed, beyond what the CI/CD pipeline automatically verifies. |
| Screenshots (UI) | For any Frontend Layer change, visual confirmation against [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)/[87_Component_Library.md](87_Component_Library.md) compliance. |
| Review Checklist | A structured checklist a reviewer works through (Deferred to Architecture for its exact content), ensuring review consistency across different reviewers. |
| Approval | At least one qualified reviewer's explicit sign-off before merge. |

## Responsibilities

- Every pipeline stage failure must block merge — no stage is advisory-only in a way that allows a failing check to be silently overridden without an explicit, logged exception process.
- Every pull request must carry a Linked Requirement — a change with no traceable requirement is a signal of scope not grounded in this specification, per the same discipline [23_Use_Case_Catalog.md](23_Use_Case_Catalog.md) established for functional requirements.

## Constraints

- This document does not specify the CI/CD platform (GitHub Actions, GitLab CI, Jenkins, etc.) — Deferred to Architecture.
- This document does not specify exact branch protection rules or required-approval counts — Deferred to Architecture.

## Future Considerations

- As the team scales, the branch strategy's `develop`-branch integration model should be reassessed against trunk-based development alternatives, which some engineering organizations prefer at scale for reducing merge complexity — this is a legitimate future reconsideration, not a defect in the current model.

## Acceptance Criteria

- [ ] All thirteen CI/CD pipeline stages from the governing specification are defined in execution order.
- [ ] The CI/CD Automation and Conventional Commits Decision Rationales are included.
- [ ] All six branch types and the Conventional Commits requirement are defined.
- [ ] All seven Code Review elements from the governing specification are defined.
