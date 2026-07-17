# 106 — Requirement Traceability

## Purpose

This document provides the complete, seven-dimension traceability framework required by Part 10: for every one of the 30 functional domains, it maps the owning Architecture Component, Data Component, API category, Frontend Module, Background Job/Worker, applicable Test type, and Deployment Component. This extends [26_Requirement_Traceability.md](26_Requirement_Traceability.md) (Part 2), which traced domains to goals/principles/use-cases, with the implementation-facing dimensions Part 10 requires.

## Scope

This document provides domain-level traceability (30 rows), not exhaustive per-requirement traceability (which would require a 200-row × 7-column matrix). Per Finding 2 in [105_Final_Architecture_Review.md](105_Final_Architecture_Review.md), full per-requirement traceability is a tooling-maintained artifact derived from this framework plus [22_Requirement_Catalog.md](22_Requirement_Catalog.md)'s domain assignment for each Requirement ID — any individual requirement's full traceability is obtained by looking up its domain here.

## Definitions

- **Traceability Dimension** — One of the seven implementation facets a requirement must be traceable to, per Part 10's mandate.

## How to Derive Full Per-Requirement Traceability

For any Requirement ID (e.g., `FR-KI-005`): (1) look up its domain in [22_Requirement_Catalog.md](22_Requirement_Catalog.md) (Knowledge Ingestion); (2) look up that domain's row in the table below for its seven-dimension mapping. This two-step lookup is deterministic and complete for all 200 requirements without requiring 200 individually authored rows.

## Domain Traceability Matrix

| Domain | Architecture Component | Data Component | API Category | Frontend Module | Background Job/Worker | Test Types | Deployment Component |
|---|---|---|---|---|---|---|---|
| Identity | Backend Layer | Organization/Workspace (PostgreSQL) | Public, Administrative | Workspace Switcher, Admin Dashboard | — | Unit, Integration, E2E (Administration) | Backend container |
| Workspace | Backend Layer | Workspace Lifecycle State (PostgreSQL) | Administrative | Admin Dashboard | — | Unit, Integration | Backend container |
| Organization | Backend Layer | Organization (PostgreSQL) | Administrative | Admin Dashboard | — | Unit, Integration | Backend container |
| User Management | Backend Layer | User (PostgreSQL) | Public, Administrative | Profile Menu, Admin Dashboard | Notification Worker | Unit, Integration, E2E (Authentication) | Backend container |
| Authentication | Authentication Layer | Session/Credential (PostgreSQL, Redis) | Public (auth endpoints) | Login UI | — | Unit, Integration, E2E, Security Testing | Backend container |
| Authorization | Authorization Layer | Role/PermissionGrant (PostgreSQL) | Internal | (enforced server-side; no dedicated UI) | — | Unit, Integration, Security Testing (Permission) | Backend container |
| Connector | Connector Layer | Connector/SyncRun (PostgreSQL) | Connector | Connector Health Dashboard | Connector Worker | Integration, E2E (Connector Sync) | Backend + Worker containers |
| Knowledge Ingestion | Knowledge Layer | Document metadata (PostgreSQL), binary (MinIO) | Internal | Document Upload UI | Connector Worker, pipeline orchestration | Integration, E2E (Document Upload) | Backend + Worker containers |
| Knowledge Processing | Knowledge Layer | Chunk (PostgreSQL) | Internal | — | OCR Worker, Embedding Worker, Entity Worker | Integration, AI Evaluation Tests | Worker containers |
| Knowledge Storage | Knowledge Layer | Document Version (PostgreSQL), binary (MinIO) | Public (download) | Document Management UI | Cleanup Worker | Integration, Performance Tests | Backend + Worker containers |
| Knowledge Graph | Knowledge Layer | Knowledge Entity/Relationship (Neo4j) | Public | Graph View | Relationship Worker | Integration, E2E (Knowledge Graph) | Backend + Neo4j |
| Enterprise Search | Retrieval Layer | Search index (OpenSearch) | Public | Search Experience | Search Worker | Integration, E2E, Performance (Search Latency) | Backend + OpenSearch |
| Retrieval | Retrieval Layer | Assembled Context (ephemeral) | Internal | — | — | AI Evaluation Tests (Retrieval Precision/Recall) | Backend container |
| AI Reasoning | AI Layer | Generated Answer / Message (PostgreSQL) | Public (chat) | AI Chat | — (synchronous, streamed) | AI Evaluation Tests (Grounding, Hallucination) | Backend + LLM Provider |
| Enterprise Memory | Knowledge Layer | Memory Record (PostgreSQL) | Public | Dashboard widgets | Cleanup Worker (staleness sweep) | Integration, AI Evaluation (Context Quality) | Backend container |
| Conversation | Backend Layer | Conversation/Message (PostgreSQL) | Public (chat) | AI Chat | Notification Worker | Integration, E2E (Chat) | Backend container |
| Citation | AI Layer | Citation (PostgreSQL) | Public | AI Chat citation display | — | AI Evaluation Tests (Citation Accuracy) | Backend container |
| Confidence | AI Layer | Confidence Score | Public | AI Chat confidence indicator | — | AI Evaluation Tests (Confidence Calibration) | Backend container |
| Document Management | Backend Layer | Document/Collection (PostgreSQL) | Public | Document Management UI | — | Integration, E2E (Document Upload) | Backend container |
| Meeting Intelligence | Knowledge Layer | Meeting (PostgreSQL), recording (MinIO) | Public | Dashboard, Search Experience | Entity Worker, Relationship Worker | Integration, AI Evaluation Tests | Backend + Worker containers |
| Decision Intelligence | Backend Layer | Decision (PostgreSQL) | Public | Search Experience (Decision Search) | — | Integration, E2E | Backend container |
| Expertise Discovery | Backend Layer | Expertise Signal (Neo4j, PostgreSQL) | Public | Search Experience (Expert Search) | Analytics Worker | Integration | Backend + Neo4j |
| Analytics | Analytics Layer | Analytics Report (PostgreSQL) | Administrative | Dashboard | Analytics Worker | Integration | Backend + Worker containers |
| Administration | Administration Layer | (composition; no primary state) | Administrative | Admin Dashboard | — | E2E (Administration) | Backend container |
| Monitoring | Monitoring Layer | Health Status (ephemeral) | Administrative | Dashboard (System Health) | — | Integration (Health Checks) | All containers (instrumentation) |
| Audit | Backend Layer | Audit Record (PostgreSQL, append-only) | Administrative | Admin Dashboard (Audit) | — | Integration, Security Testing | Backend container |
| Configuration | Configuration Layer | Configuration Setting (PostgreSQL, Redis cache) | Administrative | Admin Settings UI | — | Integration | Backend + Redis |
| Security | Infrastructure Layer | Secret / Encryption Key Reference | (cross-cutting; no dedicated surface) | — | — | Security Testing (all types) | Infrastructure / secrets backend |
| Notification | Backend Layer | Notification (PostgreSQL) | Public, Webhook | Notification Center | Notification Worker | Integration, E2E | Backend + Worker containers |
| API | Backend Layer (API Domain) | API Version / Webhook Registration (PostgreSQL) | All categories | (consumed by every frontend module) | — | API Tests | Backend container |

## Responsibilities

- Every new domain added in a later phase must receive a row in this matrix before implementation begins, completing all seven dimensions.
- This matrix must be kept synchronized with [21_Domain_Model.md](21_Domain_Model.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md) — a domain's Architecture Component here must match its stated component in those documents.

## Constraints

- This document does not provide per-requirement (200-row) traceability — see "How to Derive Full Per-Requirement Traceability" above for the two-step lookup that produces it on demand.
- "—" in a cell means the dimension does not apply to that domain (e.g., Authorization has no dedicated Frontend Module since it is enforced server-side, not a user-facing surface).

## Future Considerations

- A machine-readable export of this matrix (joined with [22_Requirement_Catalog.md](22_Requirement_Catalog.md)) should be generated once implementation tooling exists, providing genuine per-requirement traceability queryable by any of the seven dimensions — realizing [26_Requirement_Traceability.md](26_Requirement_Traceability.md)'s Future Considerations.

## Acceptance Criteria

- [ ] All 30 domains have a complete row across all seven traceability dimensions.
- [ ] The method for deriving full per-requirement traceability from this framework is explicit and correct.
- [ ] Every Architecture Component cited matches its definition in [30_System_Architecture.md](30_System_Architecture.md)/[35_Domain_Architecture.md](35_Domain_Architecture.md).
