# 05 — Target Users

## Purpose

This document identifies who Cerebrum is built for. It establishes the organizational roles and functions that later use-case, permission, and interface design must serve.

## Scope

This document covers user roles and functions at the organizational level. It does not cover specific workflows (see [06_Use_Cases.md](06_Use_Cases.md)) or access-control architecture, which is a later-phase design concern governed by the Security by Default and Least Privilege principles in [04_Project_Principles.md](04_Project_Principles.md).

## Definitions

- **Role** — An organizational function that implies a distinct pattern of knowledge need, not necessarily a job title.
- **Target User** — A role Cerebrum is explicitly designed to serve, as opposed to a role that may incidentally benefit from the platform.

## Target User Roles

Cerebrum is designed to serve the following organizational roles:

1. **Knowledge Workers** — Employees whose day-to-day work depends on finding and applying existing organizational knowledge.
2. **Software Engineers** — Individuals who need code, architecture, and technical decision context.
3. **Engineering Managers** — Individuals who need visibility into technical history, decisions, and team knowledge.
4. **Project Managers** — Individuals who need cross-system visibility into project status, decisions, and dependencies.
5. **Executives** — Individuals who need synthesized, trustworthy answers without needing to know which underlying system holds the answer.
6. **HR** — Individuals who need policy, process, and organizational knowledge.
7. **Legal** — Individuals who need traceable, citation-backed answers for compliance and risk purposes.
8. **Finance** — Individuals who need accurate, sourced organizational data for reporting and decision-making.
9. **Sales** — Individuals who need fast access to product, customer, and competitive knowledge.
10. **Customer Success** — Individuals who need historical context on customer interactions and product knowledge.
11. **Operations** — Individuals who need process documentation and cross-functional visibility.
12. **Support Teams** — Individuals who need fast, accurate answers grounded in documentation and prior resolutions.
13. **Administrators** — Individuals responsible for configuring, maintaining, and governing the Cerebrum platform itself within their organization.

## Responsibilities

- Every use case in [06_Use_Cases.md](06_Use_Cases.md) must map to at least one target user role listed here.
- Later-phase permission design must ensure that each role's access to knowledge respects the access boundaries of the source systems that knowledge came from, per the Security by Default and Least Privilege principles.
- Interface and workflow design in later phases should account for the differing technical literacy and needs across these roles (e.g., an Executive's synthesized-answer need differs from a Software Engineer's need for exact source code retrieval).

## Constraints

- This list defines who Cerebrum is designed for. It does not imply that every role receives identical functionality — role-specific experience design is a later-phase concern.
- This document does not define authentication, authorization, or identity provider integration. Those are architecture-phase concerns that must nonetheless respect the roles enumerated here.

## Future Considerations

- As Cerebrum is adopted across different industries, additional industry-specific roles (e.g., Clinical, Compliance Officer in regulated industries) may need to be added. Any such addition should go through governance review to confirm it does not imply new non-goals.
- A future phase should define whether roles map to a formal permission model (e.g., role-based access control) or whether access is purely inherited from source-system permissions. This is tracked as an open question in [11_Open_Questions.md](11_Open_Questions.md).

## Acceptance Criteria

- [ ] All thirteen target user roles from the governing specification are listed.
- [ ] Each role is described in terms of its knowledge need, not a job-title-only listing.
- [ ] The document does not prescribe interface or permission implementation details.
