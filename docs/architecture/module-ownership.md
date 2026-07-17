# Module Ownership

## Governance Context

Overall architectural authority rests with the **Architecture Owner** role
defined in `docs/architecture/specification/109_Project_Governance.md` —
the individual or body with final authority to approve ADRs and resolve
specification conflicts. That role's specific named assignment is tracked
as Open Question 130
(`docs/architecture/specification/114_Open_Questions.md`) and is an
organizational prerequisite, not something this document can assign.

This document tracks ownership one level down: which team or individual
is accountable for which module day-to-day, once modules exist. It works
alongside `.github/CODEOWNERS`, which enforces review requirements at the
same granularity.

## Current State

No domain has been implemented yet (Repository Foundation milestone). The
table below is a template, populated as each domain lands, mirroring
`docs/architecture/specification/106_Requirement_Traceability.md`'s
domain list.

| Domain | Backend Location | Owner | Status |
|---|---|---|---|
| Identity | `domain/identity/`, `application/identity/` | _unassigned_ | Not started |
| Workspace | `domain/workspace/` | _unassigned_ | Not started |
| Organization | `domain/organization/` | _unassigned_ | Not started |
| User Management | `domain/user_management/` | _unassigned_ | Not started |
| Authentication | `domain/authentication/` | _unassigned_ | Not started |
| Authorization | `domain/authorization/` | _unassigned_ | Not started |
| *(remaining 24 domains)* | — | _unassigned_ | Not started |

See `docs/architecture/specification/106_Requirement_Traceability.md` for
the complete 30-domain list with each domain's full architecture-component
mapping.

## Updating This Document

When a domain's implementation begins:

1. Add its backend location(s) once the subpackage is created.
2. Assign an owner (a person or team, not "everyone").
3. Add the corresponding path pattern to `.github/CODEOWNERS`.
4. Update Status from "Not started" to "In progress" and eventually
   "Stable."

## Cross-Cutting Components

Components spanning multiple domains (e.g., the Configuration Layer, the
Security Domain) are owned collectively by the Architecture Owner until a
dedicated team forms around them — see
`docs/architecture/specification/109_Project_Governance.md`'s Future
Considerations on this exact scaling question.
