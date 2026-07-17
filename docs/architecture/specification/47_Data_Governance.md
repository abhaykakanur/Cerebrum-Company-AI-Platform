# 47 — Data Governance

## Purpose

This document defines Cerebrum's data governance standards: the authoritative-ownership matrix, auditability requirements (which actions produce audit records), the soft-delete strategy, retention/hard-delete governance, and naming conventions. It operationalizes Data Architecture Principles 1, 9, 10, 11, and 12 from [41_Data_Architecture.md](41_Data_Architecture.md).

## Scope

This document covers governance standards and policy. It does not cover physical integrity enforcement mechanisms (see [48_Data_Integrity.md](48_Data_Integrity.md)) or tenant isolation (see [46_Multi_Tenancy.md](46_Multi_Tenancy.md)).

## Definitions

- **Authoritative Ownership Matrix** — A record of which datastore, and ultimately which functional domain, is accountable for each entity category's correctness.
- **Retention Sweep** — The Background Processing Task that evaluates entities against their applicable Retention Policy and performs hard deletion where eligible.

## Data Ownership Matrix

Every entity category's authoritative owner is stated in [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md) at the datastore level; this section restates ownership at the *domain* level (who is accountable for the data being correct), directly implementing Principle 1:

| Entity Category Group | Accountable Domain |
|---|---|
| Organization, Workspace | Identity, Workspace, Organization Domains |
| User, Team | User Management Domain |
| Connector, Knowledge Source | Connector Domain |
| Document, Document Version, Chunk | Knowledge Storage Domain, Knowledge Processing Domain |
| Embedding | Knowledge Processing Domain |
| Knowledge Entity, Knowledge Relationship, Technology | Knowledge Graph Domain |
| Conversation, Message | Conversation Domain |
| Meeting | Meeting Intelligence Domain |
| Decision | Decision Intelligence Domain |
| Project, Customer, Incident, Memory, Policy | Enterprise Memory Domain |
| Procedure | Document Management Domain |
| Search Session | Enterprise Search Domain |
| Citation | Citation Domain |
| Audit Event | Audit Domain |
| Configuration, Feature Flag | Configuration Domain |
| Background Job | Background Processing Layer |
| Notification | Notification Domain |

A data-quality or correctness defect in a given entity category is routed to its accountable domain, not treated as an undifferentiated "data team" concern — this matches the domain-ownership structure established in [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Auditability

Every action in the following list SHALL produce an `Audit Event` record (per [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)), satisfying FR-AU-001 and Data Architecture Principle 10:

| Action | Triggering Domain |
|---|---|
| Login, Logout | Authentication Domain |
| Document Upload, Document Delete | Knowledge Ingestion Domain, Knowledge Storage Domain |
| Connector Creation, Connector Failure | Connector Domain |
| Permission Change, Role Assignment | Authorization Domain |
| Search | Enterprise Search Domain |
| AI Response | AI Reasoning Domain, Conversation Domain |
| Configuration Change | Configuration Domain |
| Knowledge Update, Graph Modification | Knowledge Graph Domain, Knowledge Processing Domain |
| Embedding Regeneration | Knowledge Processing Domain |

Each `Audit Event` record SHALL include, at minimum, the fields defined in FR-AU-001's acceptance criteria (actor, action, affected resource, timestamp, outcome) plus the Base Entity Envelope's `tenant_id`/`workspace_id` for tenant-scoped query per [46_Multi_Tenancy.md](46_Multi_Tenancy.md).

**Search and AI Response auditability note:** Per Open Question 37 in [27_Open_Questions.md](27_Open_Questions.md), access to Search and AI Response audit records carries elevated sensitivity (query-content surveillance) and SHALL itself be permission-restricted beyond ordinary Audit Domain read access — this document does not resolve that access-control mechanism, only confirms the underlying records are captured.

## Provenance (Principle 9)

Beyond the Content Provenance Envelope's AI/human distinction ([44_Global_Entity_Model.md](44_Global_Entity_Model.md), Principle 6), every entity's Base Entity Envelope `Created By` field SHALL record its provenance *mechanism*, using one of: `MANUAL_ENTRY` (direct user action), `CONNECTOR_SYNC` (produced by a Connector Domain sync run, with a reference to the specific `SyncRun`), `EXTRACTION_PIPELINE` (produced by the Knowledge Processing/Graph pipeline, with a reference to the specific pipeline Task execution), or `MIGRATION` (produced by a data migration, with a reference to the migration identifier). This is distinct from Principle 6's AI/human distinction: a `CONNECTOR_SYNC`-provenance Document is neither AI-generated nor manually authored within Cerebrum — it originated externally, and provenance tracking must capture that third case.

## Soft Delete Strategy

Every business entity (every category in [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s taxonomy except purely structural/append-only categories like Audit Event, which are never deleted at all short of retention-policy expiry) SHALL contain, per the Base Entity Envelope:

| Field | Purpose |
|---|---|
| `deleted` | Boolean flag; `true` once soft-deleted. |
| `deleted_at` | Timestamp of soft deletion. |
| `deleted_by` | The actor who performed the soft deletion. |
| `restore_token` | An opaque token permitting restoration within the applicable grace period, per FR-WS-005/FR-UM-006's pattern of recoverable deletion. |

**Binding rule:** Hard deletion is prohibited except through the Retention Sweep. No domain's application service SHALL expose a direct hard-delete operation; every user- or administrator-facing "delete" action performs a soft delete, and physical removal occurs later, exclusively via the Retention Sweep evaluating the entity against its Retention Policy, directly implementing Principles 11 and 12.

## Retention and Hard Deletion Governance

- Every entity category subject to hard deletion has an applicable `RetentionPolicy` record (PostgreSQL-owned, per [42_Database_Responsibilities.md](42_Database_Responsibilities.md)), scoped at organization or workspace level per FR-KS-004.
- The Retention Sweep (a Background Processing Task per [36_Background_Processing.md](36_Background_Processing.md)) evaluates soft-deleted entities whose `deleted_at` plus the applicable grace period has elapsed, and whose Retention Policy does not place them under legal hold (Deferred to Architecture for legal-hold mechanics, per Open Question 5 in [11_Open_Questions.md](11_Open_Questions.md)).
- Hard deletion cascades per [48_Data_Integrity.md](48_Data_Integrity.md)'s No Orphan Records rule — deleting a Document's PostgreSQL row only after its Qdrant Embeddings, Neo4j-derived Knowledge Entities/Relationships (where solely sourced from this Document), and MinIO binary have all been confirmed removed, or accepting an eventually-consistent cleanup Task if a secondary store is temporarily unreachable (never leaving PostgreSQL's row deleted while secondary-store data silently persists forever).

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Database Tables | `snake_case` | `document_versions` |
| Columns | `snake_case` | `created_at` |
| UUID Columns | `<entity>_id` | `document_id` |
| Foreign Keys | `<entity>_id` (matching the referenced entity's own identifier column name) | `workspace_id` on the `documents` table |
| Indexes | `idx_<table>_<column>` | `idx_documents_workspace_id` |
| Unique Constraints | `uq_<table>_<column>` | `uq_users_email` |
| Primary Keys | `pk_<table>` | `pk_documents` |

These conventions apply to PostgreSQL schema design; Neo4j labels/property names and Qdrant collection/payload-field names follow the same `snake_case` convention for consistency, adapted to each technology's own naming rules (e.g., Neo4j node labels are conventionally `PascalCase` per Neo4j community convention — Deferred to Architecture to confirm whether Cerebrum follows Neo4j's own convention or overrides it for cross-store consistency, tracked in [49_Open_Questions.md](49_Open_Questions.md)).

## Responsibilities

- Every new table, column, index, or constraint introduced in a later phase must follow the naming conventions above; a schema review that finds a deviation should require correction before merge, not a follow-up ticket.
- Every new entity category must be added to the Data Ownership Matrix and, if it produces auditable actions, to the Auditability table, before implementation.

## Constraints

- This document does not specify exact retention periods (a business/legal decision, per Open Question 5 in [11_Open_Questions.md](11_Open_Questions.md)) — only the mechanism by which retention policy is evaluated and enforced.
- Naming conventions apply to schema-level identifiers only, not to business data values.

## Future Considerations

- As new datastores are potentially added (per [12_Future_Expansion.md](12_Future_Expansion.md)), their naming conventions should be reconciled with this document's `snake_case` standard to the extent each technology's idioms allow.

## Acceptance Criteria

- [ ] The Data Ownership Matrix covers all entity category groups from [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s taxonomy.
- [ ] All fourteen auditable actions from the governing specification are listed with their triggering domain.
- [ ] The Soft Delete Strategy's four fields match the governing specification exactly, with the hard-delete-only-via-retention binding rule explicit.
- [ ] All seven naming convention categories from the governing specification are defined with an example.
