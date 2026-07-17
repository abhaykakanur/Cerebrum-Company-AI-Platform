# 07 — Non-Goals

## Purpose

This document defines what Cerebrum explicitly does not do. Its purpose is to protect the product's focus by preventing scope creep into adjacent enterprise software categories, and to clarify that Cerebrum augments those categories rather than replacing them.

## Scope

This document covers category-level exclusions. It does not cover implementation-technology exclusions (see [03_Product_Definition.md](03_Product_Definition.md), "What Cerebrum Is Not") or feature-level exclusions, which are a later-phase concern once architecture begins.

## Definitions

- **Non-Goal** — A category of functionality Cerebrum deliberately does not provide, either because it is out of mission scope or because it properly belongs to an existing system Cerebrum should integrate with rather than replace.
- **Augmentation** — Cerebrum's relationship to existing enterprise systems: it reads from and adds intelligence on top of them, rather than replacing their functionality.

## Explicit Non-Goals

Cerebrum is **not**:

- An ERP (Enterprise Resource Planning) system.
- A CRM (Customer Relationship Management) system.
- HR software.
- Payroll software.
- Accounting software.
- Project management software.
- An IDE (Integrated Development Environment).
- A replacement for Slack.
- A replacement for GitHub.
- A replacement for Jira.
- A replacement for Confluence.

## Governing Principle

**Cerebrum augments existing enterprise systems.** It does not replace the systems of record listed above, or others like them. Cerebrum's role is to read, understand, structure, and reason over the knowledge these systems contain — not to reimplement their transactional or collaborative functionality.

## Responsibilities

- Any future proposal to add transactional functionality (e.g., issue creation, payroll processing, CRM record editing) to Cerebrum must be treated as a scope change requiring governance review, not a routine feature addition.
- Connector design in later phases must default to read access against source systems unless a specific, reviewed use case requires write-back, consistent with Least Privilege in [04_Project_Principles.md](04_Project_Principles.md).
- Product and marketing communications about Cerebrum must not imply it replaces any system listed in this document.

## Constraints

- This list is illustrative of categories, not exhaustive of every specific product Cerebrum will never touch. The governing test is the principle above: augmentation, not replacement.
- A future connector to a system in this list (e.g., a connector that reads from an ERP for knowledge extraction purposes) does not violate this document, provided it does not attempt to replace that system's core transactional function.

## Future Considerations

- As Cerebrum matures, boundary cases may arise (e.g., should Cerebrum ever support commenting on a document it surfaces, which starts to resemble collaboration-tool functionality?). Such cases should be resolved through governance review against the augmentation principle above, and logged as ADRs.
- If future business strategy intentionally moves Cerebrum into one of these categories, this document must be formally revised through the process in [09_Governance.md](09_Governance.md) — it must not be silently contradicted by a shipped feature.

## Acceptance Criteria

- [ ] All eleven explicit non-goals from the governing specification are listed.
- [ ] The augmentation principle is stated clearly enough to serve as a test for future scope decisions.
- [ ] The document distinguishes between "reading from" a listed system (permitted) and "replacing" it (not permitted).
