# 65 — Connector Architecture

## Document Status

CES Version 1.0, Phase 0, Part 6. This document extends CES Phase 0 Parts 1–5 (documents 00–64) and does not rewrite them. It elaborates the Connector Domain and Connector Layer first architected in [35_Domain_Architecture.md](35_Domain_Architecture.md) and [31_Component_Architecture.md](31_Component_Architecture.md) (Part 3) and the functional requirements FR-CN-001 through FR-CN-012 (Part 2) into a complete connector subsystem architecture.

## Purpose

This document defines the Connector Design Principles, the fifteen internal components comprising the connector subsystem, and the complete, expanded catalog of supported connector categories. It is the entry point into the Part 6 document set's connector half.

## Scope

This document covers connector subsystem-level architecture and the connector catalog. It does not cover the SDK/plugin interface in implementation-relevant detail (see [66_Connector_SDK.md](66_Connector_SDK.md)), lifecycle stage sequencing (see [67_Connector_Lifecycle.md](67_Connector_Lifecycle.md)), or synchronization mechanics (see [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)). No code, database schema, or API definition appears in this document or any Part 6 document.

## Definitions

See [10_Glossary.md](10_Glossary.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Connector Domain entry. No new terms are introduced beyond those needed for the fifteen components below.

## Connector Design Principles

Every connector SHALL satisfy the following thirteen principles, each already partially established in Part 2/3 and restated here as the binding standard for the expanded connector catalog:

| # | Principle | Established In |
|---|---|---|
| 1 | Have one responsibility (sync from exactly one source-system category). | Single Responsibility, [34_Architecture_Principles.md](34_Architecture_Principles.md) |
| 2 | Be independently configurable. | FR-CN-005 |
| 3 | Support incremental synchronization. | FR-CN-004 |
| 4 | Support full synchronization. | FR-CN-003 |
| 5 | Support health monitoring. | FR-CN-006 |
| 6 | Support retries. | FR-CN-007 |
| 7 | Support resumable synchronization. | New emphasis — see [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Retry Strategy. |
| 8 | Support structured logging. | FR-CN-009, [38_Observability.md](38_Observability.md) |
| 9 | Support observability. | [38_Observability.md](38_Observability.md) |
| 10 | Support versioning. | New — the connector plugin's own version, distinct from content versioning; see [66_Connector_SDK.md](66_Connector_SDK.md). |
| 11 | Support permission synchronization. | New emphasis — see [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Permission Synchronization. |
| 12 | Support metadata extraction. | FR-CN-010; see [69_Metadata_Extraction.md](69_Metadata_Extraction.md). |
| 13 | Support future connector upgrades. | FR-CN-012's extensibility requirement; see [66_Connector_SDK.md](66_Connector_SDK.md). |

## The Fifteen Connector Subsystem Components

The Connector Layer ([31_Component_Architecture.md](31_Component_Architecture.md)) is internally composed of the following fifteen components. This is a finer-grained decomposition than Part 3 specified, analogous to how Part 5 decomposed the AI Layer/Retrieval Layer into twelve AI Subsystem Layers.

| # | Component | Responsibility |
|---|---|---|
| 1 | Connector Registry | Maintains the catalog of available connector plugins and their capabilities; the runtime source of truth for "which connector categories exist," backing FR-CN-011. |
| 2 | Connector SDK | The `ConnectorPort` interface and shared base implementation every connector plugin builds on. See [66_Connector_SDK.md](66_Connector_SDK.md). |
| 3 | Authentication Layer | Manages per-connector credential exchange and refresh (FR-CN-001), distinct from Cerebrum's own Authentication Domain — this authenticates *Cerebrum to the source system*, not a Cerebrum user. |
| 4 | Synchronization Engine | Executes full and incremental sync runs (FR-CN-003/004). See [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md). |
| 5 | Scheduling Engine | Resolves configured sync intervals and manual triggers into executed sync runs (FR-CN-005). |
| 6 | Metadata Extraction Engine | Extracts the fifteen metadata fields defined in [69_Metadata_Extraction.md](69_Metadata_Extraction.md) from source content. |
| 7 | Permission Synchronization Engine | Synchronizes source-system access control state per [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Permission Synchronization section. |
| 8 | Document Fetch Engine | Retrieves the actual content payload for a discovered item, handing off to the Knowledge Ingestion Domain (FR-KI-003). |
| 9 | Webhook Handler | Receives and processes inbound, source-system-pushed change notifications, enabling Real-time Webhook Synchronization (see [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Synchronization Modes). |
| 10 | Delta Detection Engine | Identifies what changed since the last sync (FR-CN-004). See [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Delta Detection section. |
| 11 | Retry Engine | Implements the Retry Strategy (exponential backoff, circuit breaker, DLQ readiness) per FR-CN-007. See [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md). |
| 12 | Health Monitor | Tracks and exposes the ten Connector Health fields per FR-CN-006. See [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md). |
| 13 | Connector Configuration Manager | Owns per-connector configuration (scope, schedule, credentials reference), realizing FR-CN-005 and integrating with [37_Configuration_Strategy.md](37_Configuration_Strategy.md). |
| 14 | Connector Event Publisher | Publishes domain events (`SyncCompleted`, `ConnectorHealthDegraded`, etc.) per the Event-Driven-Ready pattern ([34_Architecture_Principles.md](34_Architecture_Principles.md)), consumed by Notification Domain (FR-NT-003) and Monitoring Layer. |
| 15 | Connector Metrics Collector | Aggregates per-connector metrics feeding [73_Search_Analytics.md](73_Search_Analytics.md)-adjacent Connector Analytics (FR-AL-004) and [38_Observability.md](38_Observability.md). |

Every component above resides within the Connector Domain's `infrastructure/`- and `application/`-layer packages per [33_Directory_Structure.md](33_Directory_Structure.md); none introduces a new bounded context beyond the single Connector Domain already established in [35_Domain_Architecture.md](35_Domain_Architecture.md) — this is internal decomposition, not a new domain.

## Supported Connector Categories: Expanded Catalog

This catalog extends FR-CN-011's 23-connector list from [20_Functional_Requirements.md](20_Functional_Requirements.md) with a substantially larger, category-organized set. Per FR-CN-012's extensibility requirement, this expansion requires no architectural change — every entry below is a new `ConnectorPort` implementation, nothing more.

**Governance note:** This document supersedes FR-CN-011's specific enumeration as the authoritative, current connector catalog, consistent with the extensibility this specification always anticipated (see [12_Future_Expansion.md](12_Future_Expansion.md)'s "Connector Coverage" future-expansion area). FR-CN-011 itself remains valid as the *requirement* that a supported-connector catalog exist and follow the framework; this document is that catalog's authoritative, current content, and future updates to the catalog should be made here rather than by editing Part 2's [20_Functional_Requirements.md](20_Functional_Requirements.md).

### Enterprise Collaboration
Slack, Microsoft Teams, Discord (future), Mattermost (future)

### Knowledge Management
Confluence, Notion, SharePoint, Google Drive, OneDrive, Dropbox, Box

### Source Control
GitHub, GitLab, Bitbucket, Azure DevOps

### Project Management
Jira, Linear, Azure Boards, ClickUp, Asana, Trello

### Communication
Gmail, Microsoft Outlook, Exchange

### Databases
PostgreSQL, MySQL, SQL Server, Oracle, MongoDB, Redis, Snowflake, BigQuery

### Object Storage
Amazon S3, Azure Blob Storage, Google Cloud Storage, MinIO

### Generic / Extensible
REST APIs, GraphQL APIs, Webhook Sources, Filesystem, Local Upload

**"(future)" designation:** Discord and Mattermost are catalogued but not committed to an initial general-availability wave, consistent with the roadmap-sequencing deferral already established in Open Question 21 of [27_Open_Questions.md](27_Open_Questions.md) — their inclusion here documents intent, not a delivery commitment.

## Responsibilities

- Every new connector category added to this catalog must implement all fifteen components' expectations (or explicitly document a stated exception, e.g., a Filesystem connector may have no meaningful Authentication Layer interaction) before being considered complete.
- The Connector Registry (component 1) is the single source of truth for catalog membership at runtime; this document is the design-time specification the registry's content must trace back to.

## Constraints

- This document does not specify per-connector implementation detail (API endpoints, rate limits, authentication flow specifics per source system) — Deferred to Architecture, per-connector, at implementation time.
- Database and Object Storage connector categories (PostgreSQL, MySQL, S3, etc.) read *from* these systems as a Knowledge Source per Cerebrum's augmentation principle ([07_Non_Goals.md](07_Non_Goals.md)) — Cerebrum does not become a database client application; it extracts structured/unstructured content from them as organizational knowledge.

## Future Considerations

- As the catalog grows, this document should track connector categories by delivery status (Available / In Development / Future) rather than a flat list, once a formal roadmap exists.

## Acceptance Criteria

- [ ] All thirteen Connector Design Principles from the governing specification are stated and traced to their Part 2/3 origin or flagged as new.
- [ ] All fifteen connector subsystem components from the governing specification are defined with a clear responsibility.
- [ ] The full expanded connector catalog from the governing specification is represented, organized by the eight stated categories.
- [ ] The relationship between this catalog and FR-CN-011 from Part 2 is explicitly reconciled, not left as a silent contradiction.
