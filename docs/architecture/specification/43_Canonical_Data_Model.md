# 43 — Canonical Data Model

## Purpose

This document is the authoritative logical data model for Cerebrum: for each of the 30 entity categories, it states the authoritative datastore, any derived cross-store representations, key conceptual attributes, its relationships to other entity categories, and whether versioning and AI/human provenance distinction apply. This is the model every future schema and ORM definition must trace back to.

## Scope

This document covers logical entity structure and storage mapping. It does not define column types, constraints (see [48_Data_Integrity.md](48_Data_Integrity.md)), or the universal envelope fields every entity shares (see [44_Global_Entity_Model.md](44_Global_Entity_Model.md), assumed present on every entity below and not repeated per-row). "Key Conceptual Attributes" names business-meaningful fields only, not the universal envelope.

## Definitions

See [10_Glossary.md](10_Glossary.md), [41_Data_Architecture.md](41_Data_Architecture.md), and [44_Global_Entity_Model.md](44_Global_Entity_Model.md). No new terms are introduced here.

## How to Read This Model

Every entity category below implicitly carries the Base Entity Envelope from [44_Global_Entity_Model.md](44_Global_Entity_Model.md) (UUID, timestamps, tenant/workspace ID, lifecycle state, soft-delete flag). "Versioned" marks entities to which the Versioning Model (also in [44_Global_Entity_Model.md](44_Global_Entity_Model.md)) applies. "AI/Human Distinguishable" marks content-bearing entities to which the Content Provenance Envelope applies.

## Entity Model

### Organization
- **Authoritative Store:** PostgreSQL. **Derived:** None.
- **Key Attributes:** Name, primary domain, industry, size, branding (logo reference, color scheme), lifecycle state (FR-OR-001).
- **Relationships:** Has many Workspaces, Users, Connectors.
- **Versioned:** No (profile changes are tracked via Audit Events, not full versioning). **AI/Human Distinguishable:** N/A.

### Workspace
- **Authoritative Store:** PostgreSQL. **Derived:** None.
- **Key Attributes:** Name, description, icon, lifecycle state, configuration (owner org's inherited or overridden settings).
- **Relationships:** Belongs to one Organization; has many Users (via membership), Documents, Connectors, Knowledge Sources.
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### User
- **Authoritative Store:** PostgreSQL. **Derived:** Redis (active session cache, ephemeral).
- **Key Attributes:** Email, name, avatar reference, job role, department, language, timezone, lifecycle state (active/deactivated/suspended/soft-deleted).
- **Relationships:** Belongs to one Organization; member of many Workspaces; has one Manager (self-referential); authors many Documents, Messages, Decisions.
- **Versioned:** No (profile history via Audit Events). **AI/Human Distinguishable:** N/A.

### Connector
- **Authoritative Store:** PostgreSQL (configuration and sync-run history). **Derived:** None; credentials referenced via Security Domain, not duplicated.
- **Key Attributes:** Source-system category (one of the 23 in FR-CN-011), configuration (scope, sync interval), health status, last sync timestamp.
- **Relationships:** Belongs to one Workspace; produces many Knowledge Sources and Documents.
- **Versioned:** No (configuration changes via Audit Events). **AI/Human Distinguishable:** N/A.

### Knowledge Source
- **Authoritative Store:** PostgreSQL.
- **Key Attributes:** Logical source name (e.g., "Engineering Confluence Space"), source-native identifier, scope description.
- **Relationships:** Belongs to one Connector; has many Documents.
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### Document
- **Authoritative Store:** PostgreSQL (metadata). **Derived:** MinIO (original binary), Qdrant (via Chunks), Neo4j (via extracted Knowledge Entities/Relationships).
- **Key Attributes:** Title, source location/path, file type, size, language, classification tags, MinIO object key reference.
- **Relationships:** Belongs to one Workspace and one Knowledge Source (nullable, for manual uploads); has many Document Versions, Chunks; authored/uploaded by one User (nullable, for connector-sourced content).
- **Versioned:** Yes — see Document Version below. **AI/Human Distinguishable:** Yes (a Document may itself be AI-generated, e.g., a meeting summary saved as a document).

### Document Version
- **Authoritative Store:** PostgreSQL (version metadata). **Derived:** MinIO (versioned binary, where the underlying format supports full-content versions).
- **Key Attributes:** Major/minor/patch version numbers, change summary, version status (current/superseded), parent version reference.
- **Relationships:** Belongs to one Document; authored by one User or one Connector sync event.
- **Versioned:** N/A (this entity *is* the version record). **AI/Human Distinguishable:** Inherits from parent Document.

### Chunk
- **Authoritative Store:** PostgreSQL (chunk text and metadata). **Derived:** Qdrant (embedding vector).
- **Key Attributes:** Sequence position within document, extracted text, chunk boundary type (semantic/fixed), quality assessment (FR-KP-010).
- **Relationships:** Belongs to one Document Version; has one or more Embeddings; referenced by many Citations.
- **Versioned:** Implicitly, via its parent Document Version. **AI/Human Distinguishable:** N/A (chunks are always system-extracted; provenance is inherited from source Document).

### Embedding
- **Authoritative Store:** Qdrant. **Derived:** PostgreSQL (pointer/metadata row: embedding model, version, vector ID reference).
- **Key Attributes:** Vector, embedding model identifier, model version, generation timestamp.
- **Relationships:** Belongs to one Chunk.
- **Versioned:** Yes (embedding model/version changes produce new Embedding records, per FR-KP-009's re-embedding cutover). **AI/Human Distinguishable:** N/A (always system-generated).

### Knowledge Entity
- **Authoritative Store:** Neo4j. **Derived:** None (PostgreSQL does not duplicate graph entities).
- **Key Attributes:** Entity type (Person, System, Project, etc.), display name, aliases.
- **Relationships:** Connected to other Knowledge Entities via Knowledge Relationships; referenced by many source Documents/Chunks.
- **Versioned:** Yes, via Graph Versioning (FR-KG-005). **AI/Human Distinguishable:** Yes — an entity may be system-extracted or manually corrected/created by a human reviewer (FR-KG-003/004 merge review).

### Knowledge Relationship
- **Authoritative Store:** Neo4j.
- **Key Attributes:** Relationship type, source reference(s), temporal validity range.
- **Relationships:** Connects exactly two Knowledge Entities.
- **Versioned:** Yes, via Graph Versioning. **AI/Human Distinguishable:** Yes, same basis as Knowledge Entity.

### Conversation
- **Authoritative Store:** PostgreSQL. **Derived:** Redis (active conversation working state).
- **Key Attributes:** Title/summary, participant User reference, workspace scope.
- **Relationships:** Has many Messages; belongs to one User (owner) and one Workspace.
- **Versioned:** No. **AI/Human Distinguishable:** N/A (the container itself; its Messages are individually distinguishable).

### Message
- **Authoritative Store:** PostgreSQL.
- **Key Attributes:** Content text, role (user query / AI answer), confidence score reference, citation references.
- **Relationships:** Belongs to one Conversation; an AI-answer Message references many Citations and one Confidence Score.
- **Versioned:** No (immutable once created). **AI/Human Distinguishable:** Yes — this is the canonical example of principle 6: every Message is explicitly either human-authored (query) or AI-generated (answer).

### Meeting
- **Authoritative Store:** PostgreSQL (metadata). **Derived:** MinIO (recording/transcript binary), Neo4j (linked entities).
- **Key Attributes:** Title, date, participant list, transcript reference.
- **Relationships:** Has one Meeting Summary (a specialized Message/Document), many Action Items, links to Decisions.
- **Versioned:** No. **AI/Human Distinguishable:** The Meeting record itself is factual metadata; its generated Summary and Action Items are AI-generated per principle 6.

### Decision
- **Authoritative Store:** PostgreSQL. **Derived:** Neo4j (decision graph node/relationships).
- **Key Attributes:** Description, rationale, decision date, outcome/supersession reference.
- **Relationships:** Has many Participants (Users), Evidence Links (to Documents/Chunks); may link to a Meeting; belongs to one Workspace.
- **Versioned:** No (supersession is modeled as a new Decision linked to the prior one, not an in-place version, since a superseded decision's original form must remain intact). **AI/Human Distinguishable:** Yes — a Decision may be manually recorded or extracted from a Document/Meeting.

### Project
- **Authoritative Store:** PostgreSQL (metadata). **Derived:** Neo4j (project graph node).
- **Key Attributes:** Name, description, status.
- **Relationships:** Has many contributing Users (via Project Involvement Records), Documents, Decisions.
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### Technology
- **Authoritative Store:** Neo4j.
- **Key Attributes:** Name, category (language, framework, tool).
- **Relationships:** Connected to Users (skill mapping), Projects, Documents mentioning it.
- **Versioned:** No. **AI/Human Distinguishable:** N/A (a factual, non-generative entity).

### Team
- **Authoritative Store:** PostgreSQL.
- **Key Attributes:** Name, description.
- **Relationships:** Has many Users (via Team Membership); belongs to one Organization.
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### Policy
- **Authoritative Store:** PostgreSQL (metadata) + MinIO (binary, if uploaded) — modeled as a specialized Document.
- **Key Attributes:** Effective-version status (current/superseded), policy category.
- **Relationships:** Is-a Document; may supersede a prior Policy.
- **Versioned:** Yes (inherits Document versioning; effective-status is additionally tracked per FR-EM-008). **AI/Human Distinguishable:** Inherits from Document.

### Procedure
- **Authoritative Store:** PostgreSQL (metadata) + MinIO (binary) — modeled as a specialized Document, same pattern as Policy.
- **Key Attributes:** Procedure category, related Policy reference.
- **Relationships:** Is-a Document.
- **Versioned:** Yes (inherits Document versioning). **AI/Human Distinguishable:** Inherits from Document.

### Customer
- **Authoritative Store:** PostgreSQL (metadata). **Derived:** Neo4j (customer graph node).
- **Key Attributes:** Name, account identifier (business identifier, not primary key per principle 3).
- **Relationships:** Has many related Documents, Decisions, Incidents (Customer Memory, FR-EM-007).
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### Incident
- **Authoritative Store:** PostgreSQL (metadata). **Derived:** Neo4j (linked entities).
- **Key Attributes:** Title, severity, status, timeline.
- **Relationships:** Links to Decisions (outcome tracking), Documents (investigation evidence), Customers (if customer-impacting).
- **Versioned:** No. **AI/Human Distinguishable:** N/A (factual record; any AI-generated incident summary is a Message/Document, not the Incident record itself).

### Memory
- **Authoritative Store:** PostgreSQL (per FR-EM-001–010's `MemoryRecord`). **Derived:** References into Neo4j/Qdrant/MinIO for underlying content, not duplicated.
- **Key Attributes:** Memory category (conversation/decision/architecture/project/employee/meeting/customer/policy), staleness signal, freshness signal.
- **Relationships:** References the underlying entity it categorizes (a Decision, Meeting, Document, etc.).
- **Versioned:** No (it is itself a categorization layer over versioned source entities). **AI/Human Distinguishable:** N/A (a Memory record's provenance is inherited from what it references).

### Search Session
- **Authoritative Store:** PostgreSQL (durable history). **Derived:** Redis (active session state).
- **Key Attributes:** Query text, result count, filters applied, executing User.
- **Relationships:** Belongs to one User and one Workspace.
- **Versioned:** No. **AI/Human Distinguishable:** N/A (the query is always human-issued; results are not stored as content here).

### Citation
- **Authoritative Store:** PostgreSQL.
- **Key Attributes:** Claim text excerpt, verification status (FR-CT-003), source reference.
- **Relationships:** Belongs to one Message (AI answer); references one Chunk (and transitively, one Document).
- **Versioned:** No (immutable once created, tied to its immutable parent Message). **AI/Human Distinguishable:** N/A (a Citation is metadata about an AI-generated claim, not itself independently authored).

### Audit Event
- **Authoritative Store:** PostgreSQL, append-only.
- **Key Attributes:** Actor, action type, affected resource reference, outcome, timestamp.
- **Relationships:** References the actor (User or system process) and the affected entity of any category.
- **Versioned:** No (immutable, append-only by design — see [48_Data_Integrity.md](48_Data_Integrity.md)). **AI/Human Distinguishable:** N/A.

### Configuration
- **Authoritative Store:** PostgreSQL. **Derived:** Redis (cache).
- **Key Attributes:** Setting key, value, scope (organization/workspace).
- **Relationships:** Belongs to one Organization or Workspace.
- **Versioned:** No (changes via Audit Events). **AI/Human Distinguishable:** N/A.

### Feature Flag
- **Authoritative Store:** PostgreSQL. **Derived:** Redis (cache).
- **Key Attributes:** Flag key, enabled state, scope.
- **Relationships:** Belongs to one Organization or Workspace.
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### Background Job
- **Authoritative Store:** PostgreSQL (durable history). **Derived:** Redis (in-flight queue state).
- **Key Attributes:** Task type, status, retry count, DLQ flag.
- **Relationships:** References the entity it operates on (a Document being processed, a Connector being synced).
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

### Notification
- **Authoritative Store:** PostgreSQL.
- **Key Attributes:** Notification type, content, read status, delivery channel.
- **Relationships:** Belongs to one User; references the triggering event/entity.
- **Versioned:** No. **AI/Human Distinguishable:** N/A.

## Entity Relationship Summary

The following relationships cross entity categories most significantly and are worth stating explicitly since they span datastores:

- `Document` —(has many)→ `Chunk` —(has one or more)→ `Embedding` (PostgreSQL → PostgreSQL → Qdrant)
- `Document`/`Chunk` —(extracted into)→ `Knowledge Entity`/`Knowledge Relationship` (PostgreSQL → Neo4j)
- `Message` (AI answer) —(cites)→ `Citation` —(references)→ `Chunk` (PostgreSQL → PostgreSQL → PostgreSQL, with the Chunk's Embedding used only during retrieval, not at citation-display time)
- `Meeting` —(produces)→ `Decision`, `Action Item` (PostgreSQL → PostgreSQL, with Neo4j derived links)
- `Memory` —(categorizes)→ any versioned, provenance-bearing entity (a thin PostgreSQL layer over the rest of the model)

## Responsibilities

- Every new entity category proposed in a later phase must receive an entry in this document, following the same structure (Authoritative Store, Derived, Key Attributes, Relationships, Versioned, AI/Human Distinguishable) before implementation begins.
- Any schema design that stores an entity's authoritative representation in a datastore other than what this document specifies requires an ADR per [09_Governance.md](09_Governance.md).

## Constraints

- "Key Attributes" are illustrative of the entity's business meaning, not an exhaustive column list — exact fields, types, and constraints are Deferred to Architecture-time schema design, governed by [48_Data_Integrity.md](48_Data_Integrity.md)'s rules.
- This document assumes, but does not repeat, the Base Entity Envelope and Versioning/Provenance models from [44_Global_Entity_Model.md](44_Global_Entity_Model.md) for every applicable entity.

## Future Considerations

- As new entity categories are identified during architecture implementation (e.g., a dedicated "Skill" entity distinct from the Technology graph node), they should be added here with full traceability to the functional requirement that motivates them.

## Acceptance Criteria

- [ ] All 30 entity categories from the governing specification have a complete entry.
- [ ] Every entity's authoritative store is consistent with [42_Database_Responsibilities.md](42_Database_Responsibilities.md)'s per-datastore "Owns" lists.
- [ ] Versioning and AI/Human distinguishability are explicitly addressed (yes/no/inherits/N/A) for every entity, not silently omitted.
