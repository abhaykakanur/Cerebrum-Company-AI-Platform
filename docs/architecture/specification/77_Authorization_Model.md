# 77 — Authorization Model

## Purpose

This document defines the complete Authorization Service architecture: supported authorization capabilities, the eight-field Permission Model, the seventeen Resource Types, and the sixteen Supported Actions. It elaborates FR-AUTZ-001 through FR-AUTZ-006 from [20_Functional_Requirements.md](20_Functional_Requirements.md) and the Authorization Domain architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Scope

This document covers the permission data model and its scope. It does not cover the specific default roles (see [78_RBAC_Model.md](78_RBAC_Model.md)) or authentication (see [76_Authentication_Architecture.md](76_Authentication_Architecture.md)).

## Definitions

- **Permission** — A single, granular grant of one or more Allowed Actions against one Resource Type within a defined Scope.
- **ABAC (Attribute-Based Access Control)** — A more expressive authorization model where access decisions consider arbitrary attributes of the actor, resource, and context, rather than only role membership.

## Authorization Capabilities

| Capability | Status | Requirement Traceability |
|---|---|---|
| RBAC | Version 1 | FR-AUTZ-001 |
| ABAC | Ready (future) | New — see Decision Rationale below for why RBAC precedes it |
| Hierarchical Roles | Supported | Extends FR-AUTZ-001; see [78_RBAC_Model.md](78_RBAC_Model.md) |
| Permission Inheritance | Supported | FR-AUTZ-002 |
| Workspace Permissions | Supported | FR-AUTZ-003 |
| Document Permissions | Supported | FR-AUTZ-003 |
| Connector Permissions | Supported | New explicit resource scope, elaborating FR-AUTZ-003/FR-CN-001's least-privilege connector scoping |
| Administration Permissions | Supported | FR-AUTZ-004 |
| AI Feature Permissions | Supported | New — governs access to AI Subsystem Layer capabilities per [62_AI_Governance.md](62_AI_Governance.md)'s configuration surface, distinct from content-level permissions |
| Search Permissions | Supported | FR-ES-010 |
| Knowledge Graph Permissions | Supported | FR-KG-006's permission-filtered traversal |

### Decision Rationale: Why RBAC Before ABAC

RBAC (Role-Based Access Control) is adopted for Version 1.0, with ABAC (Attribute-Based Access Control) architected as a future-ready extension rather than built initially, for three reasons consistent with principles already established: (1) Simple architecture over unnecessary complexity ([04_Project_Principles.md](04_Project_Principles.md)) — RBAC's role-to-permission model is sufficient to express the permission needs identified across [20_Functional_Requirements.md](20_Functional_Requirements.md)'s Authorization Domain requirements, while ABAC's arbitrary-attribute evaluation introduces policy-engine complexity not yet justified by a concrete unmet need; (2) the Permission Model below (Resource Type + Scope + Allowed Actions) is intentionally designed to be extensible toward attribute-based conditions later — an ABAC migration extends this model's Scope field with attribute predicates rather than replacing the model; (3) Explainability ([04_Project_Principles.md](04_Project_Principles.md)) — RBAC's role-membership-based decisions are easier for both administrators and the FR-ES-009 Result Explanation requirement to state in human terms ("you have this role, which grants this permission") than ABAC's potentially complex attribute-combination logic, which matters given this platform's binding Explainability principle applies to authorization decisions as much as to AI-generated answers.

## Permission Model

Every Permission SHALL have the following eight fields:

| Field | Description |
|---|---|
| Permission ID | Unique identifier, per the Base Entity Envelope ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)). |
| Name | Human-readable identifier (e.g., "Document: Read"). |
| Description | What the permission grants, in plain language, supporting Explainability. |
| Scope | Organization, Workspace, or a specific resource instance — the boundary within which this permission applies, per [46_Multi_Tenancy.md](46_Multi_Tenancy.md)'s tenant scoping and [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Authorization Domain. |
| Resource Type | One of the seventeen types below. |
| Allowed Actions | One or more of the sixteen actions below. |
| Inheritance Rules | How this permission propagates per FR-AUTZ-002's inheritance model (e.g., workspace-level grant cascading to contained documents unless overridden). |
| Audit Metadata | Creation/modification provenance, per FR-AUTZ-006's permission-change auditing, reusing the Base Entity Envelope. |

## Resource Types

Authorization SHALL be scoped to the following seventeen resource types, extending FR-AUTZ-003's baseline (workspace/document/knowledge/search/administrative) with the complete enumeration:

Organizations, Workspaces, Users, Connectors, Documents, Folders, Knowledge Graph, Search, AI Chat, Memories, Meetings, Projects, Policies, Configurations, Analytics, Audit Logs, Administration.

Each resource type corresponds to an entity category or domain already established in [44_Global_Entity_Model.md](44_Global_Entity_Model.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md) — no new entity category is introduced here; this is the authorization-relevant grouping of existing categories, at the granularity Permission scoping requires (e.g., "AI Chat" corresponds to the Conversation Domain; "Memories" to the Enterprise Memory Domain).

## Supported Actions

Permissions SHALL grant one or more of the following sixteen actions:

Create, Read, Update, Delete, Search, Upload, Download, Share, Manage, Configure, Synchronize, Execute, Approve, Export, Restore, Archive.

Not every action applies to every Resource Type (e.g., "Synchronize" applies to Connectors, not to Users) — the valid Resource Type × Action combinations are Deferred to Architecture as an implementation-time matrix, but every combination that is valid must draw its action name from this fixed sixteen-action vocabulary, preventing an ad hoc, per-resource-type action naming scheme from emerging.

## Responsibilities

- Every new Resource Type or Action introduced in a later phase must be added to these two enumerations before use — an authorization check referencing an undeclared Resource Type or Action is invalid by construction.
- The ABAC readiness claim must be periodically validated as new Resource Types or permission-scoping needs emerge — if a genuine attribute-based need arises before ABAC is built, it should trigger the migration evaluation described in the Decision Rationale above, not an ad hoc RBAC workaround that erodes the model's clarity.

## Constraints

- This document does not specify the Resource Type × Action validity matrix — Deferred to Architecture.
- This document does not specify how ABAC, once built, would extend the Scope field — Deferred to Architecture at that future point.

## Future Considerations

- The AI Feature Permissions resource-scope introduced here should be reconciled with [62_AI_Governance.md](62_AI_Governance.md)'s configuration-level AI settings access as that document's administrative surface matures — the two are related (both gate AI capability access) but serve different purposes (feature access vs. configuration authority).

## Acceptance Criteria

- [ ] All eleven authorization capabilities from the governing specification are listed with status, including the RBAC-before-ABAC Decision Rationale.
- [ ] All eight Permission Model fields from the governing specification are defined.
- [ ] All seventeen Resource Types from the governing specification are listed and traced to an existing entity category or domain.
- [ ] All sixteen Supported Actions from the governing specification are listed.
