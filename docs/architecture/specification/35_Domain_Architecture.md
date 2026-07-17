# 35 — Domain Architecture

## Purpose

This document defines the architecture of each of the 30 functional domains from [20_Functional_Requirements.md](20_Functional_Requirements.md): purpose, responsibilities, public interfaces, internal components, dependencies, forbidden dependencies, and ownership. It applies the patterns defined in [34_Architecture_Principles.md](34_Architecture_Principles.md) to each specific bounded context, and refines the Owns/Depends On relationships first established in [21_Domain_Model.md](21_Domain_Model.md) with architecture-specific detail.

## Scope

This document covers per-domain architecture. It does not restate requirement acceptance criteria (see [20_Functional_Requirements.md](20_Functional_Requirements.md)) or high-level component grouping (see [30_System_Architecture.md](30_System_Architecture.md)). "Public Interfaces" and "Internal Components" name conceptual ports, services, entities, and value objects — never concrete method signatures or code.

## Definitions

See [10_Glossary.md](10_Glossary.md) and [34_Architecture_Principles.md](34_Architecture_Principles.md). No new terms are introduced here.

## Global Forbidden Dependency Rules

Every domain's "Forbidden Dependencies" field below references one or more of these global rules, defined once here to avoid repetition:

- **G1:** A domain's `domain/` layer shall never import from any `infrastructure/` package, its own or another's.
- **G2:** A domain shall never import another domain's `infrastructure/` or internal `domain/` submodules directly — only another domain's published `application/` service interface.
- **G3:** No backend domain shall be imported by the Frontend Layer, or shall itself import anything from the Frontend Layer.
- **G4:** A Connector Layer plugin shall never be imported directly by the Knowledge Layer or any other domain — only via the Connector Layer framework's defined handoff contract.

---

## 1. Identity Domain

- **Purpose:** Establish the root tenant (Organization) and sub-tenant (Workspace) identity records all other domains anchor to.
- **Responsibilities:** Organization/workspace creation, profile, branding (FR-ID-001–005).
- **Public Interfaces:** `IdentityApplicationService` (createOrganization, createWorkspace, updateProfile, updateBranding).
- **Internal Components:** `Organization` entity, `Workspace` entity, `OrganizationProfile` / `WorkspaceProfile` value objects, `IdentityFactory` (enforces creation invariants).
- **Dependencies:** None (foundational domain). Actor authentication is enforced by API-layer middleware ahead of every domain call, per [30_System_Architecture.md](30_System_Architecture.md)'s Authentication Layer description — this is a cross-cutting interceptor concern, not a domain-to-domain dependency, so Identity does not list Authentication as a dependency.
- **Forbidden Dependencies:** G1, G2. Identity shall never depend on Workspace, Organization, or Authentication Domain application services — those domains depend on Identity, not the reverse. This resolves what would otherwise be a circular dependency (Identity → Authentication → User Management → Identity) present if actor verification were modeled as a domain-level call.
- **Ownership:** `Organization`, `Workspace` root records (identity facts only; lifecycle state owned by Workspace/Organization Domains below).

## 2. Workspace Domain

- **Purpose:** Own the operational lifecycle of a Workspace after creation.
- **Responsibilities:** Lifecycle state, configuration, ownership, transfer, deletion, archival (FR-WS-001–006).
- **Public Interfaces:** `WorkspaceApplicationService` (transitionLifecycle, configure, transferOwnership, delete, archive).
- **Internal Components:** `WorkspaceLifecycleState` value object, `WorkspaceOwnershipGrant` entity, `WorkspaceConfiguration` value object, `WorkspaceLifecyclePolicy` domain service (validates legal state transitions).
- **Dependencies:** Identity Domain, Authorization Domain (ownership/administrative permission checks).
- **Forbidden Dependencies:** G1, G2. Workspace shall never depend on Knowledge Layer domains directly for its archival behavior — it raises a `WorkspaceArchived` domain event that the Knowledge Layer subscribes to.
- **Ownership:** Workspace Lifecycle State, Workspace Configuration, Workspace Ownership Grant.

## 3. Organization Domain

- **Purpose:** Own organization-wide lifecycle and cascading default settings.
- **Responsibilities:** Lifecycle state, multi-workspace structure, settings inheritance (FR-OR-001–003).
- **Public Interfaces:** `OrganizationApplicationService` (transitionLifecycle, listWorkspaces, setDefault, resolveEffectiveSetting).
- **Internal Components:** `OrganizationLifecycleState` value object, `OrganizationSettingsDefault` entity, `SettingsInheritanceResolver` domain service.
- **Dependencies:** Identity Domain.
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Organization Lifecycle State, Organization Settings Default.

## 4. User Management Domain

- **Purpose:** Own the lifecycle and profile of individual user accounts.
- **Responsibilities:** Registration, invitation, activation, deactivation, suspension, soft delete, profile/preferences, organizational relationships (FR-UM-001–008).
- **Public Interfaces:** `UserApplicationService` (register, invite, activate, deactivate, suspend, softDelete, updateProfile, updateRelationships).
- **Internal Components:** `User` aggregate root, `UserProfile` / `UserPreferenceSet` value objects, `TeamMembership` / `ManagerRelationship` entities, `UserLifecyclePolicy` domain service.
- **Dependencies:** Identity Domain. User Management does not synchronously depend on Authentication: session invalidation on deactivation/suspension (FR-UM-004, FR-UM-005) is achieved by publishing a `UserDeactivated`/`UserSuspended` domain event that Authentication subscribes to, keeping the relationship one-way and avoiding a cycle with Authentication's own synchronous dependency on User Management for credential lookup.
- **Forbidden Dependencies:** G1, G2. User Management shall never depend on Expertise Discovery Domain — the dependency runs the other way (Expertise Discovery consumes User Management's published relationship-change events). User Management shall never issue a synchronous call into Authentication's application service, per the event-based relationship above.
- **Ownership:** User Account, User Profile, User Preference Set, Team Membership, Manager Relationship.

> **Note on relationship refinement:** This entry refines User Management's relationship to Authentication from [21_Domain_Model.md](21_Domain_Model.md) (Part 2), which listed Authentication as a plain "Depends On" without distinguishing direction of call. Part 3's circular-dependency verification found that a synchronous dependency in both directions (Authentication → User Management for credential lookup, User Management → Authentication for session invalidation) would form a 2-node cycle; the event-based resolution above preserves both required behaviors without one.

## 5. Authentication Domain

- **Purpose:** Verify actor identity and manage sessions.
- **Responsibilities:** Credential verification, password reset, magic link, OAuth/SSO/MFA readiness, session management, device trust, account recovery (FR-AUTH-001–009).
- **Public Interfaces:** `AuthenticationApplicationService` (authenticate, resetPassword, issueMagicLink, validateSession, manageDevice, recoverAccount).
- **Internal Components:** `Credential` entity, `Session` aggregate root, `DeviceTrustRecord` entity, `PasswordResetToken` / `MagicLinkToken` value objects, `CredentialVerificationPolicy` domain service.
- **Dependencies:** User Management Domain (actor existence), Infrastructure Layer (Security — signing keys, secrets).
- **Forbidden Dependencies:** G1, G2. Authentication shall never depend on Authorization — it establishes identity, never permission.
- **Ownership:** Credential, Session, Device Trust Record, Password Reset Token, Magic Link Token.

## 6. Authorization Domain

- **Purpose:** Own all resource-scoped access-control decisions.
- **Responsibilities:** RBAC, permission inheritance, resource-scoped permissions, administrative tiers, least-privilege defaults, permission-change auditing (FR-AUTZ-001–006).
- **Public Interfaces:** `AuthorizationApplicationService` (checkPermission, filterByPermission, assignRole, grantPermission, revokePermission).
- **Internal Components:** `Role` entity, `PermissionGrant` value object, `PermissionInheritanceRule` domain service, `LeastPrivilegeDefaultPolicy` domain service.
- **Dependencies:** Authentication Domain (verified actor), User Management Domain, Identity Domain.
- **Forbidden Dependencies:** G1, G2. Every other domain that calls Authorization does so via its published `checkPermission`/`filterByPermission` interface only — no domain shall reimplement permission logic locally.
- **Ownership:** Role, Permission Grant, Permission Inheritance Rule.

## 7. Connector Domain

- **Purpose:** Own authenticated, monitored synchronization with external source systems.
- **Responsibilities:** Connector auth, validation, full/incremental sync, health, scheduling, retry, conflict handling, logging, metadata extraction, extensibility (FR-CN-001–012).
- **Public Interfaces:** `ConnectorApplicationService` (configureConnector, triggerSync, getHealth); `ConnectorPort` (the plugin contract every connector implements: authenticate, validate, fullSync, incrementalSync, reportHealth).
- **Internal Components:** `ConnectorConfiguration` entity, `SyncRun` aggregate root, `ConnectorHealthStatus` value object, `ConflictResolutionPolicy` / `RetryPolicy` domain services.
- **Dependencies:** Authorization Domain (least-privilege scoping), Infrastructure Layer (Security — credential storage), Background Processing Layer (sync execution).
- **Forbidden Dependencies:** G1, G2, G4. The Connector Domain's shared framework shall never depend on any individual connector plugin — dependency runs plugin → framework only.
- **Ownership:** Connector Configuration, Sync Run, Connector Health Status.

## 8. Knowledge Ingestion Domain

- **Purpose:** Own the intake pipeline entry point for all content, regardless of origin.
- **Responsibilities:** Upload (manual/bulk/folder), connector-sourced and scheduled/incremental ingestion, duplicate/version detection, metadata extraction, language detection, OCR trigger, normalization, failure recovery, reporting (FR-KI-001–012).
- **Public Interfaces:** `IngestionApplicationService` (ingest, reportStatus).
- **Internal Components:** `IngestionJob` aggregate root, `IngestedItem` (pre-processing) entity, `DuplicateDetector` / `VersionDetector` domain services, `IngestionReport` value object.
- **Dependencies:** Connector Domain, Authorization Domain (permission metadata capture).
- **Forbidden Dependencies:** G1, G2. Ingestion shall never write directly to the Knowledge Storage Domain's final index — it hands off to Knowledge Processing first.
- **Ownership:** Ingestion Job, Ingested Item (pre-processing), Ingestion Report.

## 9. Knowledge Processing Domain

- **Purpose:** Transform normalized, ingested content into structured, searchable, reasoning-ready knowledge.
- **Responsibilities:** Text/image/table extraction, OCR, language normalization, chunking, enrichment, keyword/entity/relationship/topic extraction, embedding generation, quality validation (FR-KP-001–010).
- **Public Interfaces:** `ProcessingApplicationService` (process, getQualityAssessment).
- **Internal Components:** `ProcessedContentChunk` entity, `ExtractionResult` value object, `QualityAssessment` value object, `ChunkingStrategy` / `QualityValidationPolicy` domain services.
- **Dependencies:** Knowledge Ingestion Domain, Infrastructure Layer (Embedding Providers).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Processed Content Chunk, Extraction Result, Quality Assessment.

## 10. Knowledge Storage Domain

- **Purpose:** Own durable, versioned persistence of content and its derivatives.
- **Responsibilities:** Persistent storage, metadata storage, version history, retention, archival/restore, delete/soft delete, integrity verification (FR-KS-001–007).
- **Public Interfaces:** `StorageApplicationService` (store, getVersion, applyRetention, archive, restore, delete, verifyIntegrity).
- **Internal Components:** `StoredItem` aggregate root, `ItemVersion` entity, `RetentionPolicy` value object, `ArchivalState` value object.
- **Dependencies:** Knowledge Processing Domain, Infrastructure Layer (Persistence — object storage, relational metadata store).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Stored Item, Item Version, Retention Policy, Archival State.

## 11. Knowledge Graph Domain

- **Purpose:** Own the structured entity/relationship representation of organizational knowledge.
- **Responsibilities:** Entity/relationship creation, merging, duplicate resolution, versioning, traversal, timeline, visualization data (FR-KG-001–008).
- **Public Interfaces:** `GraphApplicationService` (createEntity, createRelationship, merge, traverse, getTimeline, getVisualizationData).
- **Internal Components:** `GraphEntity` aggregate root, `GraphRelationship` entity, `GraphVersion` value object, `DuplicateResolutionPolicy` domain service.
- **Dependencies:** Knowledge Processing Domain (extraction output), Knowledge Storage Domain, Authorization Domain (traversal permission filtering).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Graph Entity, Graph Relationship, Graph Version.

## 12. Enterprise Search Domain

- **Purpose:** Own query-time, human-facing search execution across all indexed content.
- **Responsibilities:** Keyword/semantic/hybrid/metadata/faceted/graph search, autocomplete, ranking, explanation, permission enforcement (FR-ES-001–010).
- **Public Interfaces:** `SearchApplicationService` (search, autocomplete, explainResult).
- **Internal Components:** `SearchQuery` value object, `SearchResultSet` entity, `Facet` value object, `RankingPolicy` domain service.
- **Dependencies:** Knowledge Processing Domain (indexed content), Knowledge Graph Domain, Authorization Domain.
- **Forbidden Dependencies:** G1, G2. Enterprise Search shall never generate natural-language answers — that is exclusively the AI Reasoning Domain's responsibility.
- **Ownership:** Search Query, Search Result Set, Facet.

## 13. Retrieval Domain

- **Purpose:** Assemble permission-filtered, source-attributed context for AI reasoning, distinct from human-facing search.
- **Responsibilities:** Hybrid retrieval, context assembly, source ranking, deduplication, token budgeting, citation preservation, context validation (FR-RT-001–007).
- **Public Interfaces:** `RetrievalApplicationService` (assembleContext).
- **Internal Components:** `RetrievalCandidate` value object, `AssembledContext` aggregate root, `TokenBudgetPolicy` / `DeduplicationPolicy` domain services.
- **Dependencies:** Enterprise Search Domain, Knowledge Graph Domain, Authorization Domain.
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Retrieval Candidate Set, Assembled Context.

## 14. AI Reasoning Domain

- **Purpose:** Generate grounded answers strictly from assembled context.
- **Responsibilities:** Grounded generation, evidence synthesis, cross-document reasoning, query decomposition, response validation, hallucination reduction, structured output, reasoning transparency (FR-AR-001–008).
- **Public Interfaces:** `ReasoningApplicationService` (generateAnswer, getReasoningTrace).
- **Internal Components:** `ReasoningQuery` value object, `GeneratedAnswer` aggregate root, `ReasoningTrace` entity, `ResponseValidationPolicy` domain service, `LLMProviderPort` (infrastructure-facing port).
- **Dependencies:** Retrieval Domain, Citation Domain, Confidence Domain.
- **Forbidden Dependencies:** G1, G2. AI Reasoning shall never query a datastore directly — all knowledge access is through the Retrieval Domain's assembled context.
- **Ownership:** Reasoning Query, Generated Answer, Reasoning Trace.

## 15. Enterprise Memory Domain

- **Purpose:** Own categorized, durable organizational memory beyond raw document storage.
- **Responsibilities:** Conversation/decision/architecture/project/employee/meeting/customer/policy memory, knowledge aging, freshness signals (FR-EM-001–010).
- **Public Interfaces:** `MemoryApplicationService` (recordMemory, getMemory, getStalenessSignal, getFreshnessSignal).
- **Internal Components:** `MemoryRecord` entity (one subtype per category), `StalenessSignal` / `FreshnessSignal` value objects, `AgingPolicy` domain service.
- **Dependencies:** Knowledge Storage Domain (synchronous, for staleness/freshness computation over stored items). Enterprise Memory additionally **subscribes to domain events** published by Decision Intelligence Domain (`DecisionRecorded`) and Meeting Intelligence Domain (`MeetingProcessed`) to populate its Decision Memory and Meeting Memory categories, per the Event-Driven-Ready pattern in [34_Architecture_Principles.md](34_Architecture_Principles.md). Event subscription is a one-way, decoupled relationship — the publisher (Decision Intelligence, Meeting Intelligence) has no dependency on or awareness of Enterprise Memory — and is therefore not counted as a synchronous "Dependency" for circular-dependency analysis.
- **Forbidden Dependencies:** G1, G2. Enterprise Memory shall never issue a synchronous call into Decision Intelligence or Meeting Intelligence's application services; doing so would reintroduce a cycle (Meeting Intelligence depends synchronously on AI Reasoning, which depends on Confidence, which depends on Enterprise Memory — a synchronous Enterprise Memory → Meeting Intelligence edge would close that loop). Event subscription is the only permitted relationship in this direction.
- **Ownership:** Memory Record (per category), Staleness Signal, Freshness Signal.

> **Note on relationship refinement:** This document refines two dependency edges from [21_Domain_Model.md](21_Domain_Model.md) (Part 2) — Decision Intelligence's and Meeting Intelligence's relationship to Enterprise Memory — from a stated synchronous "Depends On" to the event-subscription model described above, after circular-dependency verification during Part 3 architecture work surfaced a 4-node cycle (AI Reasoning → Confidence → Enterprise Memory → Meeting Intelligence → AI Reasoning) under the original framing. Part 2's Requirement definitions (FR-EM-002, FR-EM-006, FR-DI-001) are unaffected; only the architectural realization of how Enterprise Memory obtains decision/meeting data is refined.

---

## 16. Conversation Domain

- **Purpose:** Own the multi-turn dialogue surface through which users query AI Reasoning.
- **Responsibilities:** Query submission, multi-turn context, history, export, follow-up suggestion (FR-CV-001–005).
- **Public Interfaces:** `ConversationApplicationService` (submitQuery, resumeConversation, exportConversation, getHistory).
- **Internal Components:** `Conversation` aggregate root, `ConversationTurn` entity, `FollowUpSuggestionPolicy` domain service.
- **Dependencies:** AI Reasoning Domain, Enterprise Memory Domain.
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Conversation, Conversation Turn.

## 17. Citation Domain

- **Purpose:** Own attachment, linking, and verification of source citations on generated answers.
- **Responsibilities:** Citation attachment, source linking, verification, missing-citation disclosure (FR-CT-001–004).
- **Public Interfaces:** `CitationApplicationService` (attachCitations, verifyCitation, resolveCitationLink).
- **Internal Components:** `Citation` value object, `CitationVerificationResult` value object, `CitationVerificationPolicy` domain service.
- **Dependencies:** Retrieval Domain, Authorization Domain (source-link permission checks).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Citation, Citation Verification Result.

## 18. Confidence Domain

- **Purpose:** Own computation and exposure of answer confidence.
- **Responsibilities:** Confidence scoring, display, low-confidence handling, calibration feedback (FR-CF-001–004).
- **Public Interfaces:** `ConfidenceApplicationService` (scoreConfidence, applyThresholdPolicy, recordFeedback).
- **Internal Components:** `ConfidenceScore` value object, `ConfidenceThresholdPolicy` domain service, `CalibrationFeedbackRecord` entity.
- **Dependencies:** Citation Domain, Enterprise Memory Domain (freshness input).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Confidence Score, Confidence Threshold Policy, Calibration Feedback Record.

## 19. Document Management Domain

- **Purpose:** Own direct, human-facing document interaction beyond AI reasoning input.
- **Responsibilities:** Download, preview, version history, tagging, collections, sharing, archiving (FR-DM-001–007).
- **Public Interfaces:** `DocumentManagementApplicationService` (download, preview, tag, addToCollection, share, archive).
- **Internal Components:** `DocumentTag` value object, `Collection` entity, `ShareGrant` value object.
- **Dependencies:** Knowledge Storage Domain, Knowledge Ingestion Domain, Authorization Domain.
- **Forbidden Dependencies:** G1, G2. Sharing shall never grant access beyond what Authorization already permits — Document Management has no authority to create new permission grants.
- **Ownership:** Document Tag, Collection, Share Grant.

## 20. Meeting Intelligence Domain

- **Purpose:** Extract structured knowledge from meeting transcripts.
- **Responsibilities:** Transcript ingestion, speaker identification readiness, summarization, action items, decision extraction, follow-up generation, knowledge linking (FR-MI-001–007).
- **Public Interfaces:** `MeetingIntelligenceApplicationService` (processTranscript, getSummary, getActionItems).
- **Internal Components:** `MeetingTranscript` entity, `MeetingSummary` value object, `ActionItem` entity, `SpeakerAssociationPolicy` domain service.
- **Dependencies:** Knowledge Ingestion Domain, AI Reasoning Domain, Decision Intelligence Domain, Knowledge Graph Domain.
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Meeting Transcript, Meeting Summary, Action Item.

## 21. Decision Intelligence Domain

- **Purpose:** Own structured recording and lifecycle of organizational decisions.
- **Responsibilities:** Decision recording, timeline, reasoning capture, participants, evidence links, outcome tracking (FR-DI-001–006).
- **Public Interfaces:** `DecisionApplicationService` (recordDecision, getTimeline, linkEvidence, linkOutcome).
- **Internal Components:** `DecisionRecord` aggregate root, `DecisionTimelineEntry` value object.
- **Dependencies:** Citation Domain, Knowledge Graph Domain.
- **Forbidden Dependencies:** G1, G2. Decision Intelligence shall never depend on Enterprise Memory Domain — Enterprise Memory's Decision Memory category consumes Decision Intelligence's published `DecisionRecorded` domain event (see Enterprise Memory Domain below); the dependency runs one way only, which is what keeps this relationship acyclic.
- **Ownership:** Decision Record, Decision Timeline Entry.

## 22. Expertise Discovery Domain

- **Purpose:** Identify and map who in the organization holds knowledge on a given topic.
- **Responsibilities:** Expert identification, skill/technology mapping, project mapping, knowledge ownership, availability metadata (FR-ED-001–005).
- **Public Interfaces:** `ExpertiseApplicationService` (findExperts, getSkillMap, getProjectInvolvement, getOwnership).
- **Internal Components:** `ExpertiseSignal` value object, `SkillMap` entity, `ProjectInvolvementRecord` entity, `ExpertiseRankingPolicy` domain service.
- **Dependencies:** Knowledge Graph Domain, User Management Domain (via published events, not direct dependency — see Forbidden Dependencies in User Management), Decision Intelligence Domain.
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Expertise Signal, Skill Map, Project Involvement Record.

## 23. Analytics Domain

- **Purpose:** Aggregate and report on platform usage and health.
- **Responsibilities:** Search, usage, coverage, connector, performance, adoption analytics (FR-AL-001–006).
- **Public Interfaces:** `AnalyticsApplicationService` (recordEvent [write], getReport [read]).
- **Internal Components:** `AnalyticsReport` value object, `MetricTimeSeries` entity, `ReportAggregationPolicy` domain service.
- **Dependencies:** Enterprise Search Domain, Connector Domain, Confidence Domain, Citation Domain, Conversation Domain (all as event producers, consumed asynchronously).
- **Forbidden Dependencies:** G1, G2. Analytics shall never mutate the state of any domain it reports on — read/record only.
- **Ownership:** Analytics Report, Metric Time Series.

## 24. Administration Domain

- **Purpose:** Provide consolidated, permission-gated administrative surfaces composed from other domains.
- **Responsibilities:** Workspace/user/connector administration, delegated administration (FR-AD-001–004).
- **Public Interfaces:** `AdministrationApplicationService` (administerWorkspace, administerUser, administerConnector, delegate).
- **Internal Components:** `AdministrativeDelegationGrant` value object (no independent aggregate root — this domain composes others, per [31_Component_Architecture.md](31_Component_Architecture.md)).
- **Dependencies:** Workspace Domain, User Management Domain, Connector Domain, Authorization Domain.
- **Forbidden Dependencies:** G1, G2. Administration shall never own primary state duplicating Workspace/User Management/Connector data — it orchestrates their application services only.
- **Ownership:** Administrative Delegation Grant.

## 25. Monitoring Domain

- **Purpose:** Provide real-time subsystem health visibility and degradation alerting.
- **Responsibilities:** System health monitoring, ingestion/processing monitoring, degradation alerting, uptime dashboard (FR-MN-001–004).
- **Public Interfaces:** `MonitoringApplicationService` (getHealthStatus, getUptimeHistory); shared instrumentation port consumed by all domains.
- **Internal Components:** `HealthStatus` value object, `DegradationEvent` entity, `AlertingPolicy` domain service.
- **Dependencies:** Every domain exposing a monitorable subsystem (as an instrumentation producer, not a business dependency).
- **Forbidden Dependencies:** G1, G2. Monitoring shall never trigger an automated remediation action against another domain in V1.0 — it raises a Notification Domain event only.
- **Ownership:** Health Status, Degradation Event.

## 26. Audit Domain

- **Purpose:** Own the immutable, queryable historical record of security- and governance-relevant activity.
- **Responsibilities:** Audit log capture, permission-change trail, login history, connector history, search history, administrative history (FR-AU-001–006).
- **Public Interfaces:** `AuditApplicationService` (recordAuditEvent [write, called by every domain], queryAuditHistory [read, permission-gated]).
- **Internal Components:** `AuditRecord` entity (append-only).
- **Dependencies:** Every domain producing an audit-relevant event (as an event producer via domain events, per Event-Driven-Ready in [34_Architecture_Principles.md](34_Architecture_Principles.md)).
- **Forbidden Dependencies:** G1, G2. No domain shall be able to modify or delete an `AuditRecord` through any normal application code path — mutation methods on this entity are intentionally absent.
- **Ownership:** Audit Record.

## 27. Configuration Domain

- **Purpose:** Own tunable system behavior not tied to a specific workspace identity or user account.
- **Responsibilities:** AI configuration, search configuration, feature flags, system settings (FR-CG-001–004).
- **Public Interfaces:** `ConfigurationApplicationService` (getConfig [read, cached], setConfig [write, Administration-only]).
- **Internal Components:** `ConfigurationSetting` entity, `FeatureFlag` entity, `InheritanceResolver` domain service (reused from Organization Domain's pattern, distinct instance).
- **Dependencies:** Organization Domain (settings inheritance scope).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Configuration Setting, Feature Flag.

## 28. Security Domain

- **Purpose:** Own platform-wide security controls cutting across every other domain.
- **Responsibilities:** Encryption at rest/in transit, secrets management, tenant isolation, vulnerability management, incident response (FR-SC-001–006).
- **Public Interfaces:** `SecurityInfrastructureService` (getSecret, encrypt, decrypt) — this domain is realized primarily as Infrastructure Layer capability rather than a traditional domain/application/infrastructure triad, since its concerns are inherently cross-cutting rather than aggregate-owning.
- **Internal Components:** `EncryptionKeyReference` value object, `Secret` value object (never logged, never serialized in full).
- **Dependencies:** None internally; consumed by every domain handling sensitive data.
- **Forbidden Dependencies:** G1, G2. No domain shall implement its own encryption or secrets handling independent of this domain's adapters.
- **Ownership:** Encryption Key Reference, Secret, Isolation Boundary (the tenant-scoping rule enforced at every repository port per [30_System_Architecture.md](30_System_Architecture.md)'s Security Overview).

## 29. Notification Domain

- **Purpose:** Deliver system-generated notices to users and administrators.
- **Responsibilities:** In-app and email notifications, connector failure alerts, sync/processing completion notices (FR-NT-001–005).
- **Public Interfaces:** `NotificationApplicationService` (notify, getNotifications, markRead, setPreferences).
- **Internal Components:** `Notification` entity, `NotificationPreference` value object.
- **Dependencies:** Every domain generating a notifiable event (Connector, Ingestion, Monitoring, Authorization, etc., via domain events).
- **Forbidden Dependencies:** G1, G2.
- **Ownership:** Notification, Notification Preference.

## 30. API Domain

- **Purpose:** Own the externally and internally consumable programmatic interfaces to Cerebrum.
- **Responsibilities:** Public, internal, administrative, and connector API surfaces; webhook support; versioning strategy (FR-AP-001–006).
- **Public Interfaces:** This domain *is* the interface layer — it exposes every other domain's application services through versioned HTTP routers, and owns `WebhookRegistration`.
- **Internal Components:** `APIVersion` value object, `WebhookRegistration` entity, `DeprecationPolicy` domain service.
- **Dependencies:** Every domain it exposes a surface for (calls their application services only, per G2).
- **Forbidden Dependencies:** G1, G2, G3. The API Domain shall never contain business logic duplicating a domain's application service — it is translation and routing only (request DTO ↔ application service call ↔ response DTO).
- **Ownership:** API Version, Webhook Registration.

## Dependency Graph Verification

Per the Architecture Quality Checklist's "no circular dependencies" requirement, the synchronous Dependencies graph across all 30 domains was traced end-to-end. Three latent cycles were identified and resolved during this verification, each by reclassifying one direction of a mutual relationship from a synchronous call to an asynchronous domain-event subscription (a one-way, decoupled relationship that does not create a call-graph cycle, per the Event-Driven-Ready pattern in [34_Architecture_Principles.md](34_Architecture_Principles.md)):

| Cycle Found | Resolution |
|---|---|
| Identity → Authentication → User Management → Identity | Identity has no dependencies; actor authentication is API-middleware, not a domain dependency. |
| User Management ↔ Authentication (2-node) | Authentication → User Management (credential lookup) remains synchronous; User Management → Authentication (session invalidation) becomes event-based. |
| AI Reasoning → Confidence → Enterprise Memory → Meeting Intelligence → AI Reasoning | Enterprise Memory's relationship to Meeting Intelligence and Decision Intelligence becomes event-based; only Enterprise Memory → Knowledge Storage remains synchronous. |

With these three resolutions applied, the remaining synchronous Dependencies graph across all 30 domains is a directed acyclic graph (DAG) — every domain's dependencies resolve to strictly lower-level domains, with Identity and Security as the two dependency-free foundational domains. This verification should be re-run whenever a domain's Dependencies field changes.

## Responsibilities

- Every domain added in a later phase must receive an entry in this document with all seven fields (Purpose, Responsibilities, Public Interfaces, Internal Components, Dependencies, Forbidden Dependencies, Ownership) before implementation begins.
- A pull request introducing a dependency not listed in a domain's Dependencies field, or violating its Forbidden Dependencies, should be rejected in review pending either a correction or an ADR updating this document.

## Constraints

- Interface and component names in this document are conceptual and architecture-binding in their existence and responsibility, not in their exact naming — method signatures, exact class names, and file organization beyond [33_Directory_Structure.md](33_Directory_Structure.md) are Deferred to Architecture-time implementation.
- This document does not define database schemas even where an entity is named; persistence representation is an Infrastructure Layer concern.

## Future Considerations

- As domains are extracted into independent services per the extraction-seam guidance in [31_Component_Architecture.md](31_Component_Architecture.md), each domain's Public Interfaces become its network-facing API contract with minimal translation, by design.

## Acceptance Criteria

- [ ] All 30 domains from [20_Functional_Requirements.md](20_Functional_Requirements.md) have complete entries with all seven required fields.
- [ ] Every domain's Dependencies are consistent with [21_Domain_Model.md](21_Domain_Model.md)'s Depends On relationships from Part 2.
- [ ] No domain's Forbidden Dependencies contradict its stated Dependencies.
- [ ] No circular dependency exists among the Dependencies fields across all 30 domains.