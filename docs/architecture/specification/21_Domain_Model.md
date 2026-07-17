# 21 — Domain Model

## Purpose

This document describes the 30 functional domains that organize [20_Functional_Requirements.md](20_Functional_Requirements.md): what each domain is responsible for, which other domains it depends on, and the conceptual entities it owns. It is a map of responsibility boundaries, not a data model — entity attributes, storage schema, and service boundaries are Deferred to Architecture.

## Scope

This document covers domain-level responsibility and dependency relationships only. It does not define database schemas, service topology, or API contracts. "Owns" below means a domain is the authoritative source of truth for a concept; other domains reference that concept but do not redefine it.

## Definitions

- **Domain** — A named area of functional responsibility, per [20_Functional_Requirements.md](20_Functional_Requirements.md)'s Requirement ID Scheme.
- **Owns** — The domain is the authoritative source of truth for the listed conceptual entity.
- **Depends On** — The domain's requirements assume the listed domain's capability exists and functions correctly.
- **Conceptual Entity** — A named "thing" the domain is responsible for, described by name only. Attributes, relationships, and persistence are Deferred to Architecture.

## Domain Relationship Overview

Domains cluster into six functional layers. A domain generally depends only on domains in its own layer or an earlier one; where a dependency runs "backward" (a foundational-layer domain depending on a higher-layer one), it is called out explicitly below.

| Layer | Domains |
|---|---|
| 1. Tenancy & Identity | Identity, Workspace, Organization, User Management |
| 2. Access Control | Authentication, Authorization |
| 3. Knowledge Pipeline | Connector, Knowledge Ingestion, Knowledge Processing, Knowledge Storage |
| 4. Intelligence | Knowledge Graph, Enterprise Search, Retrieval, AI Reasoning, Enterprise Memory |
| 5. Experience | Conversation, Citation, Confidence, Document Management, Meeting Intelligence, Decision Intelligence, Expertise Discovery |
| 6. Platform Operations | Analytics, Administration, Monitoring, Audit, Configuration, Security, Notification, API |

---

## Layer 1: Tenancy & Identity

### Identity Domain
- **Owns:** Organization identity record, Workspace identity record, organization/workspace profile and branding.
- **Depends On:** Authentication Domain (actor verification for creation actions).
- **Conceptual Entities:** Organization, Workspace.

### Workspace Domain
- **Owns:** Workspace lifecycle state, workspace configuration, workspace ownership.
- **Depends On:** Identity Domain, Authorization Domain.
- **Conceptual Entities:** Workspace Lifecycle State, Workspace Configuration, Workspace Ownership Grant.

### Organization Domain
- **Owns:** Organization lifecycle state, organization-to-workspace structure, organization-level setting defaults.
- **Depends On:** Identity Domain.
- **Conceptual Entities:** Organization Lifecycle State, Organization Settings Default.

### User Management Domain
- **Owns:** User account, user profile, user preferences, user organizational relationships (team, manager).
- **Depends On:** Identity Domain, Authentication Domain, Expertise Discovery Domain (relationship metadata feeds expertise mapping — a Layer 1 → Layer 5 forward reference resolved at the Expertise Discovery Domain's consuming end, not here).
- **Conceptual Entities:** User Account, User Profile, User Preference Set, Team Membership, Manager Relationship.

---

## Layer 2: Access Control

### Authentication Domain
- **Owns:** Credential verification, session, device trust.
- **Depends On:** User Management Domain.
- **Conceptual Entities:** Credential, Session, Device Trust Record, Password Reset Token, Magic Link Token.

### Authorization Domain
- **Owns:** Roles, role assignments, resource-scoped permissions, permission inheritance rules.
- **Depends On:** User Management Domain, Identity Domain.
- **Conceptual Entities:** Role, Permission Grant, Permission Inheritance Rule.

---

## Layer 3: Knowledge Pipeline

### Connector Domain
- **Owns:** Connector configuration, connector credentials, sync execution, connector health.
- **Depends On:** Authorization Domain (least-privilege scoping), Security Domain (credential storage).
- **Conceptual Entities:** Connector Configuration, Sync Run, Connector Health Status.

### Knowledge Ingestion Domain
- **Owns:** Ingestion pipeline intake, duplicate/version detection at intake, ingestion reporting.
- **Depends On:** Connector Domain, Authorization Domain.
- **Conceptual Entities:** Ingestion Job, Ingested Item (pre-processing), Ingestion Report.

### Knowledge Processing Domain
- **Owns:** Extraction, chunking, enrichment, embedding generation, quality validation.
- **Depends On:** Knowledge Ingestion Domain.
- **Conceptual Entities:** Processed Content Chunk, Extraction Result, Quality Assessment.

### Knowledge Storage Domain
- **Owns:** Durable persistence, version history, retention policy, archival/deletion state.
- **Depends On:** Knowledge Processing Domain.
- **Conceptual Entities:** Stored Item, Item Version, Retention Policy, Archival State.

---

## Layer 4: Intelligence

### Knowledge Graph Domain
- **Owns:** Entities, relationships, graph versioning and traversal.
- **Depends On:** Knowledge Processing Domain (entity/relationship extraction output), Knowledge Storage Domain.
- **Conceptual Entities:** Graph Entity, Graph Relationship, Graph Version.

### Enterprise Search Domain
- **Owns:** Query-time search execution, ranking, facets, permission-filtered results.
- **Depends On:** Knowledge Processing Domain, Knowledge Graph Domain, Authorization Domain.
- **Conceptual Entities:** Search Query, Search Result Set, Facet.

### Retrieval Domain
- **Owns:** Reasoning-context assembly, source ranking for context, token budgeting.
- **Depends On:** Enterprise Search Domain, Authorization Domain.
- **Conceptual Entities:** Retrieval Candidate Set, Assembled Context.

### AI Reasoning Domain
- **Owns:** Answer generation, evidence synthesis, response validation.
- **Depends On:** Retrieval Domain, Citation Domain, Confidence Domain.
- **Conceptual Entities:** Reasoning Query, Generated Answer, Reasoning Trace.

### Enterprise Memory Domain
- **Owns:** Categorized durable memory (conversation, decision, architecture, project, employee, meeting, customer, policy), knowledge aging signals.
- **Depends On:** Knowledge Storage Domain, Decision Intelligence Domain, Meeting Intelligence Domain.
- **Conceptual Entities:** Memory Record (per category), Staleness Signal, Freshness Signal.

---

## Layer 5: Experience

### Conversation Domain
- **Owns:** Multi-turn dialogue state, conversation history.
- **Depends On:** AI Reasoning Domain, Enterprise Memory Domain.
- **Conceptual Entities:** Conversation, Conversation Turn.

### Citation Domain
- **Owns:** Citation attachment, source linking, citation verification.
- **Depends On:** Retrieval Domain, AI Reasoning Domain, Authorization Domain.
- **Conceptual Entities:** Citation, Citation Verification Result.

### Confidence Domain
- **Owns:** Confidence scoring, low-confidence handling policy, calibration feedback.
- **Depends On:** Citation Domain, Enterprise Memory Domain (freshness signal input).
- **Conceptual Entities:** Confidence Score, Confidence Threshold Policy, Calibration Feedback Record.

### Document Management Domain
- **Owns:** Document-level human interaction surfaces (download, preview, tagging, collections, sharing, archiving).
- **Depends On:** Knowledge Storage Domain, Knowledge Ingestion Domain, Authorization Domain.
- **Conceptual Entities:** Document Tag, Collection, Share Grant.

### Meeting Intelligence Domain
- **Owns:** Transcript-derived extraction (summaries, action items, decisions, speaker association).
- **Depends On:** Knowledge Ingestion Domain, AI Reasoning Domain, Decision Intelligence Domain, Knowledge Graph Domain.
- **Conceptual Entities:** Meeting Transcript, Meeting Summary, Action Item.

### Decision Intelligence Domain
- **Owns:** Decision records, decision rationale, participants, evidence links, outcomes.
- **Depends On:** Citation Domain, Knowledge Graph Domain, Enterprise Memory Domain.
- **Conceptual Entities:** Decision Record, Decision Timeline Entry.

### Expertise Discovery Domain
- **Owns:** Expert identification, skill/technology/project mapping, knowledge ownership attribution.
- **Depends On:** Knowledge Graph Domain, User Management Domain, Decision Intelligence Domain.
- **Conceptual Entities:** Expertise Signal, Skill Map, Project Involvement Record.

---

## Layer 6: Platform Operations

### Analytics Domain
- **Owns:** Usage, search, coverage, connector, performance, and adoption reporting.
- **Depends On:** Enterprise Search Domain, Connector Domain, Confidence Domain, Citation Domain, Conversation Domain.
- **Conceptual Entities:** Analytics Report, Metric Time Series.

### Administration Domain
- **Owns:** Administrative surfaces for workspace, user, and connector management; delegated administration.
- **Depends On:** Workspace Domain, User Management Domain, Connector Domain, Authorization Domain.
- **Conceptual Entities:** Administrative Delegation Grant.

### Monitoring Domain
- **Owns:** Real-time subsystem health, degradation alerting, uptime dashboarding.
- **Depends On:** All domains exposing a monitorable subsystem.
- **Conceptual Entities:** Health Status, Degradation Event.

### Audit Domain
- **Owns:** Immutable audit log capture and retrieval across all domains.
- **Depends On:** All domains producing audit-relevant events.
- **Conceptual Entities:** Audit Record.

### Configuration Domain
- **Owns:** AI configuration, search configuration, feature flags, system settings.
- **Depends On:** Organization Domain (settings inheritance).
- **Conceptual Entities:** Configuration Setting, Feature Flag.

### Security Domain
- **Owns:** Encryption, secrets management, tenant isolation enforcement, vulnerability management, incident response.
- **Depends On:** Cross-cutting; consumed by every domain handling sensitive data.
- **Conceptual Entities:** Encryption Key Reference, Secret, Isolation Boundary.

### Notification Domain
- **Owns:** In-app and email notification delivery for system-generated events.
- **Depends On:** Every domain that generates a notifiable event (Connector, Ingestion, Monitoring, Authorization, etc.).
- **Conceptual Entities:** Notification, Notification Preference.

### API Domain
- **Owns:** Public, internal, administrative, and connector API surfaces; API versioning.
- **Depends On:** Every domain it exposes a surface for.
- **Conceptual Entities:** API Version, Webhook Registration.

## Responsibilities

- Every requirement in [20_Functional_Requirements.md](20_Functional_Requirements.md) must belong to exactly one domain's ownership as described here; cross-domain requirements list their primary domain and record secondary relevance as a dependency.
- Architecture-phase work translating this model into services, schemas, or bounded contexts must preserve these ownership boundaries or record an ADR explaining the departure, per [09_Governance.md](09_Governance.md).

## Constraints

- No conceptual entity listed here implies a specific database table, service, or API resource. That translation is Deferred to Architecture.
- Dependency arrows describe requirement-level assumptions, not necessarily runtime call direction — Deferred to Architecture.

## Future Considerations

- As Phase 1 architecture work begins, this domain model should be validated against proposed service boundaries; a significant mismatch should trigger a governance review rather than a silent architecture-side reinterpretation.
- New domains introduced after this phase (see [12_Future_Expansion.md](12_Future_Expansion.md)) must be added here with the same Owns/Depends On structure.

## Acceptance Criteria

- [ ] All 30 domains from [20_Functional_Requirements.md](20_Functional_Requirements.md) are represented.
- [ ] Every domain states what it owns and what it depends on.
- [ ] No entry prescribes a database schema, service boundary, or API contract.
