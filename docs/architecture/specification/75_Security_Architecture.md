# 75 — Security Architecture

## Document Status

CES Version 1.0, Phase 0, Part 7. This document extends CES Phase 0 Parts 1–6 (documents 00–74) and does not rewrite them. It consolidates and deepens the security architecture already established across [30_System_Architecture.md](30_System_Architecture.md)'s Security Overview, [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Authentication/Authorization/Security Domains, and [46_Multi_Tenancy.md](46_Multi_Tenancy.md), into a single authoritative security subsystem architecture.

## Purpose

This document defines the seven binding Security Principles, the twelve components of the security subsystem, and — since no dedicated document exists for them in this Part's output list — the Encryption, Secrets Management, and Audit Logging architecture. It is the entry point into the Part 7 document set's security half.

## Scope

This document covers subsystem-level security architecture, encryption, secrets, and audit logging. It does not cover authentication mechanics (see [76_Authentication_Architecture.md](76_Authentication_Architecture.md)), authorization/permission modeling (see [77_Authorization_Model.md](77_Authorization_Model.md), [78_RBAC_Model.md](78_RBAC_Model.md)), or threat-specific mitigation detail (see [79_Threat_Model.md](79_Threat_Model.md)).

## Definitions

See [10_Glossary.md](10_Glossary.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Security Domain entry. No new terms are introduced beyond what the twelve components below require.

## Security Principles

Security SHALL be enforced by default, restating and binding the following seven principles, each already established in [04_Project_Principles.md](04_Project_Principles.md) and [30_System_Architecture.md](30_System_Architecture.md):

| Principle | Enforcement |
|---|---|
| Security SHALL be enforced by default. | Least-Privilege Default Enforcement, FR-AUTZ-005. |
| Every request SHALL be authenticated. | Authentication Layer middleware, [30_System_Architecture.md](30_System_Architecture.md). |
| Every request SHALL be authorized. | Authorization Layer's `checkPermission`/`filterByPermission`, invoked at every resource-scoped operation, [35_Domain_Architecture.md](35_Domain_Architecture.md). |
| Every request SHALL be auditable. | Audit Service, this document's Audit Logging section below. |
| Least privilege SHALL always be enforced. | FR-AUTZ-005, connector default-scope (FR-CN-001). |
| Trust SHALL never be assumed. | Zero-trust posture — every request re-verified regardless of network origin or prior authentication elsewhere in the request chain; no service-to-service call is implicitly trusted without its own authentication/authorization check. |
| Security SHALL be applied consistently across all services. | The same Authentication/Authorization Layer middleware pattern applies to every one of the fifteen high-level components in [30_System_Architecture.md](30_System_Architecture.md) — no component implements its own parallel security check. |

## The Twelve Security Subsystem Components

| # | Component | Realized By | Detailed In |
|---|---|---|---|
| 1 | Identity Service | Identity Domain, User Management Domain | [35_Domain_Architecture.md](35_Domain_Architecture.md) |
| 2 | Authentication Service | Authentication Domain | [76_Authentication_Architecture.md](76_Authentication_Architecture.md) |
| 3 | Authorization Service | Authorization Domain | [77_Authorization_Model.md](77_Authorization_Model.md) |
| 4 | Role Management | Authorization Domain (`Role` entity) | [78_RBAC_Model.md](78_RBAC_Model.md) |
| 5 | Permission Management | Authorization Domain (`PermissionGrant`) | [77_Authorization_Model.md](77_Authorization_Model.md) |
| 6 | Session Management | Authentication Domain (`Session` entity) | [76_Authentication_Architecture.md](76_Authentication_Architecture.md) |
| 7 | Token Management | Authentication Domain | [76_Authentication_Architecture.md](76_Authentication_Architecture.md) |
| 8 | API Security Layer | API Domain, Authentication/Authorization middleware | [80_API_Architecture.md](80_API_Architecture.md) |
| 9 | Audit Service | Audit Domain | This document, Audit Logging section |
| 10 | Secrets Management | Security Domain | This document, Secrets Management section |
| 11 | Encryption Service | Security Domain | This document, Encryption section |
| 12 | Security Monitoring | Monitoring Domain, Security Domain | [38_Observability.md](38_Observability.md) |

No new domain is introduced by this decomposition — every component maps to an existing domain from [35_Domain_Architecture.md](35_Domain_Architecture.md), consistent with the pattern already established when Part 5 and Part 6 decomposed the AI Layer and Connector Layer into finer-grained internal components without introducing new bounded contexts.

## Encryption

Restating and completing FR-SC-001/FR-SC-002 and [30_System_Architecture.md](30_System_Architecture.md)'s Security Overview with the complete scope of what is encrypted:

**Encrypted at rest and in transit:** Passwords (never stored in plaintext — hashed, not merely encrypted, per standard security practice), Tokens, Secrets, Credentials, Connector Secrets, API Keys, Sensitive Metadata (per [63_AI_Guardrails.md](63_AI_Guardrails.md)'s PII Awareness and Sensitive Data Protection classifications).

**Encryption at Rest:** Every PostgreSQL, Neo4j, Qdrant, and MinIO datastore is encrypted at rest at the infrastructure level, per FR-SC-001.

**Encryption in Transit:** Every network hop — client to Backend Layer, Backend Layer to every datastore, Backend Layer to every external Connector target and AI Provider — uses encrypted transport, per FR-SC-002.

**Future Key Rotation:** Encryption key rotation is architected as a capability the Security Domain's `EncryptionKeyReference` value object ([35_Domain_Architecture.md](35_Domain_Architecture.md)) supports (a reference, not the key material itself, is what other components hold), but is not committed to a specific rotation cadence in V1.0 — Deferred to Architecture, tracked in [84_Open_Questions.md](84_Open_Questions.md).

## Secrets Management

**Binding rules:** Secrets SHALL never be hardcoded. Secrets SHALL be externally configurable. Both rules directly restate [37_Configuration_Strategy.md](37_Configuration_Strategy.md)'s Secrets category and the Security Domain's `GetSecret` port ([35_Domain_Architecture.md](35_Domain_Architecture.md)) — this document does not re-architect secrets handling, it confirms the following seven secret types are in scope for that existing mechanism:

API Keys, OAuth Credentials, Database Credentials, JWT Secrets, Encryption Keys, LLM Provider Keys ([60_AI_Model_Abstraction.md](60_AI_Model_Abstraction.md)'s Provider Credentials), Connector Credentials ([65_Connector_Architecture.md](65_Connector_Architecture.md)'s Authentication Layer).

### Decision Rationale: Why Externalized Secrets

Externalizing secrets (never hardcoded, always retrieved through the `GetSecret` port from a dedicated secrets backend) is the only approach compatible with three binding constraints already established: (1) the Modular Monolith's Kubernetes-Ready deployment target ([32_Technology_Stack.md](32_Technology_Stack.md)) requires secrets to be injectable per-environment without a code change; (2) Least Privilege requires that secret *access* be independently auditable and revocable from secret *storage location*, which a hardcoded secret cannot support; (3) the Naming Conventions and version-control discipline in [47_Data_Governance.md](47_Data_Governance.md) would otherwise risk a secret being committed to source control, an incident class this architecture eliminates structurally rather than relying on developer discipline to avoid.

## Audit Logging

**Binding rule:** Every security-sensitive action SHALL generate an immutable audit event, per FR-AU-001 and the Audit Domain's no-mutation-path enforcement ([35_Domain_Architecture.md](35_Domain_Architecture.md), [48_Data_Integrity.md](48_Data_Integrity.md) Rule 7). This document extends [47_Data_Governance.md](47_Data_Governance.md)'s auditable-action list with the following security-specific examples, several new to this Part:

Login, Logout, Failed Login, Password Change, Role Assignment, Permission Change, Connector Authentication, Configuration Update, API Key Rotation, Secret Update, Document Deletion, Knowledge Export.

"Failed Login," "Password Change," "API Key Rotation," and "Secret Update" are new, security-specific additions to the auditable-action list beyond what [47_Data_Governance.md](47_Data_Governance.md) enumerated — they are added here as an extension of that list, not a replacement.

### Decision Rationale: Why Immutable Audit Logs

Audit logs must be immutable because their evidentiary value for compliance audits (FR-AU-001's business justification), security-incident investigation, and permission-correctness verification depends entirely on the guarantee that a record of what happened cannot later be altered — including by the same administrator whose action is being audited. A mutable audit log would allow exactly the class of actor most likely to need auditing (a privileged administrator) to also be the actor most able to erase evidence of misuse, defeating the control's purpose. This is why [48_Data_Integrity.md](48_Data_Integrity.md) Rule 7 enforces immutability at both the application layer (no mutation use case exists) and the database layer (trigger-level rejection) as defense in depth.

## Responsibilities

- Every new security-sensitive action introduced in a later phase must be added to the Audit Logging action list before release.
- Every component in the twelve-component table must remain traceable to an existing domain — a proposed new security component introducing a new domain requires an ADR per [09_Governance.md](09_Governance.md).

## Constraints

- This document does not specify encryption algorithms, key lengths, or the specific secrets-management product — Deferred to Architecture, per Open Question 39 in [40_Open_Questions.md](40_Open_Questions.md).
- This document does not repeat the full tenant-isolation architecture — see [46_Multi_Tenancy.md](46_Multi_Tenancy.md).

## Future Considerations

- Key rotation cadence and automation should be defined once the specific secrets-management product (Open Question 39) is selected, since rotation mechanics are often product-specific.

## Acceptance Criteria

- [ ] All seven Security Principles from the governing specification are stated as binding with their enforcement mechanism.
- [ ] All twelve security subsystem components from the governing specification are defined and traced to an existing domain.
- [ ] Encryption scope (what is encrypted, at rest, in transit, future key rotation) is fully addressed.
- [ ] Secrets Management's binding rules and seven secret types are addressed, with the Externalized Secrets Decision Rationale included.
- [ ] Audit Logging's binding rule and twelve example actions are addressed, with the Immutable Audit Logs Decision Rationale included.
