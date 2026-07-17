# 78 — RBAC Model

## Purpose

This document defines Cerebrum's nine default roles, their scope, and their position in the role hierarchy. It directly resolves Open Question 18 in [27_Open_Questions.md](27_Open_Questions.md) ("What is the complete built-in role catalog beyond the minimum of Administrator, Member, and Viewer-equivalent access levels?"), which this document should be considered the ADR-equivalent answer to.

## Scope

This document covers the default role catalog and hierarchy. It does not cover the underlying Permission Model those roles are composed from (see [77_Authorization_Model.md](77_Authorization_Model.md)) or authentication (see [76_Authentication_Architecture.md](76_Authentication_Architecture.md)).

## Definitions

- **Hierarchical Role** — A role whose permission set is understood relative to its position in an ordered hierarchy, where a higher role's permission set is a superset of (or otherwise strictly more privileged than) roles below it, within the same scope.
- **Custom Role** — An organization-defined role composed from the Permission Model's building blocks ([77_Authorization_Model.md](77_Authorization_Model.md)), not one of the eight fixed default roles.

## The Nine Default Roles

| Role | Scope | Purpose | Hierarchy Position |
|---|---|---|---|
| Platform Owner | Cross-organization (Cerebrum operator only) | Operates the Cerebrum platform itself across all tenant organizations — not a customer-facing role. See the Platform Owner section below for its special governance treatment. | Above all organization-scoped roles; outside the per-organization hierarchy entirely. |
| Organization Owner | Organization | Full administrative authority within one Organization: workspace creation/deletion, organization-level configuration, billing-adjacent settings (Deferred to Architecture per [07_Non_Goals.md](07_Non_Goals.md)'s billing exclusion), and the ability to assign/revoke every other organization-scoped role. | Top of the per-organization hierarchy; corresponds to FR-AUTZ-004's organization-level administrator. |
| Workspace Administrator | Workspace | Full administrative authority within one Workspace: user invitation, connector configuration, workspace-level settings, and workspace-scoped role assignment — without organization-wide authority. | Below Organization Owner; corresponds to FR-AUTZ-004's workspace-level administrator. |
| Knowledge Manager | Workspace | Curatorial authority over knowledge quality: document tagging/classification (FR-DM-004), retention policy application within their scope, review of Knowledge Quality Validation flags (FR-KP-010), and Knowledge Graph merge-review (FR-KG-003/004). Does not carry Workspace Administrator's user/connector management authority. | Peer to Project Manager and Developer, below Workspace Administrator. |
| Project Manager | Workspace, typically scoped further to specific Projects | Authority over Project Memory (FR-EM-004), Decision recording for their projects, and project-scoped search/analytics visibility. | Peer to Knowledge Manager and Developer, below Workspace Administrator. |
| Developer | Workspace | Elevated access to Source Control and Architecture-related connectors and content (Architecture Memory, FR-EM-003; Code Query search type, [70_Enterprise_Search.md](70_Enterprise_Search.md)), without broader administrative authority. | Peer to Knowledge Manager and Project Manager, below Workspace Administrator. |
| Employee | Workspace | The standard general-member role: read/search access to workspace content per ordinary permission inheritance, conversational AI access, and creation of their own content (documents, decisions they participate in). | Below the three specialized roles above; the default role for most organization members. |
| Viewer | Workspace, or a narrower resource scope | Read-only access — search and view content, no creation, modification, sharing, or configuration authority. | The most restricted named role, below Employee. |
| Custom Roles | Organization- or Workspace-defined | Organization-composed roles built from [77_Authorization_Model.md](77_Authorization_Model.md)'s Permission Model, for needs the eight fixed roles do not precisely fit. | Positioned in the hierarchy per the organization's own configuration, validated against Permission Inheritance rules (FR-AUTZ-002) to prevent an inconsistent hierarchy position. |

## Role Hierarchy Diagram (Descriptive)

```
Platform Owner (cross-organization, Cerebrum operator only — outside the hierarchy below)

Organization Owner
    └── Workspace Administrator
            ├── Knowledge Manager
            ├── Project Manager
            └── Developer
                    └── Employee
                            └── Viewer

Custom Roles: positioned per organization configuration, anywhere below Organization Owner
```

Hierarchical Roles ([77_Authorization_Model.md](77_Authorization_Model.md)) means a role's permission set is generally a superset of the roles below it in the same branch — Workspace Administrator's permissions are a superset of Employee's within that workspace, for instance — but Knowledge Manager, Project Manager, and Developer are peer specializations, not strictly ordered relative to each other; each carries permissions the others do not, all subordinate to Workspace Administrator.

## The Platform Owner Role: Special Governance

Platform Owner is architecturally distinct from every other role in this catalog: it is held only by Cerebrum's own platform-operations personnel, never by a customer organization's staff, and its cross-organization visibility is in deliberate tension with the strict tenant isolation guarantee in [46_Multi_Tenancy.md](46_Multi_Tenancy.md). This tension is resolved, not ignored, by the following constraints:

- Platform Owner access to any specific organization's data SHALL be exceptional (e.g., a support investigation), not routine or standing.
- Every Platform Owner action touching organization-scoped data SHALL be audited with the same rigor as any other security-sensitive action ([75_Security_Architecture.md](75_Security_Architecture.md)'s Audit Logging), and SHALL be visible to the affected organization's own Organization Owner, not hidden from the customer.
- The specific access-grant mechanism (standing role vs. just-in-time elevation) is Deferred to Architecture, tracked in [84_Open_Questions.md](84_Open_Questions.md), given its direct bearing on the tenant-isolation guarantee's practical strength.

## Reconciliation with Target User Roles (Part 1)

[05_Target_Users.md](05_Target_Users.md) defined thirteen target user roles at the product-persona level (Knowledge Workers, Software Engineers, Engineering Managers, Project Managers, Executives, HR, Legal, Finance, Sales, Customer Success, Operations, Support Teams, Administrators). These are personas describing *who* uses Cerebrum and *why*; the nine RBAC roles in this document are the *access-control* mechanism assigned to those personas. The mapping is many-to-many and organization-configurable (e.g., an "Engineering Manager" persona might typically receive the Developer or Workspace Administrator RBAC role depending on the organization's structure) — this document does not fix a rigid persona-to-role mapping, since that mapping is inherently organization-specific.

## Responsibilities

- Any new default role proposed in a later phase must be positioned in the hierarchy above and evaluated against the existing eight before being added — role sprawl (near-duplicate roles with marginal distinctions) should be resisted in favor of Custom Roles for organization-specific needs.
- Platform Owner's access-grant mechanism must be finalized before general availability, given its security-sensitivity, per this document's Future Considerations.

## Constraints

- This document does not specify the exact permission set (which of [77_Authorization_Model.md](77_Authorization_Model.md)'s Resource Type × Action combinations) each default role carries — Deferred to Architecture as an implementation-time matrix, informed by this document's scope/purpose descriptions.
- Custom Roles' composability is bounded by the Permission Model's existing vocabulary ([77_Authorization_Model.md](77_Authorization_Model.md)) — an organization cannot define a Custom Role requiring a Resource Type or Action not already in that model's enumeration.

## Future Considerations

- As organizations adopt Custom Roles in practice, commonly recurring Custom Role patterns should be evaluated for promotion to a tenth default role, following the same "resist role sprawl, but don't force every organization into ill-fitting defaults" balance.

## Acceptance Criteria

- [ ] All nine default roles from the governing specification are defined with scope, purpose, and hierarchy position.
- [ ] The role hierarchy is stated clearly, including peer (non-strictly-ordered) relationships where they exist.
- [ ] Platform Owner's tension with tenant isolation is explicitly addressed, not silently glossed over.
- [ ] This document is explicitly connected to Open Question 18 in [27_Open_Questions.md](27_Open_Questions.md) as its resolution.
