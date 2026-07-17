# 66 — Connector SDK

## Purpose

This document defines the Connector SDK: the shared interface and base capability every connector plugin builds on, and the versioning/upgrade model that lets connector plugins evolve independently of the core platform. It elaborates the `ConnectorPort` interface first introduced in [31_Component_Architecture.md](31_Component_Architecture.md) and [35_Domain_Architecture.md](35_Domain_Architecture.md), and FR-CN-012's extensibility requirement.

## Scope

This document covers the SDK's architectural contract and versioning model. It does not specify actual interface method signatures, language bindings, or packaging — those are implementation details Deferred to Architecture, consistent with this phase's "do not write code" constraint.

## Definitions

- **Connector SDK** — The shared contract and base implementation every connector plugin depends on to integrate with the Connector Layer's shared components (per [65_Connector_Architecture.md](65_Connector_Architecture.md)'s fifteen components).
- **Connector Plugin** — A specific implementation of the SDK's contract for one connector category (e.g., the Slack connector plugin).
- **Connector Version** — The plugin's own version number, distinct from the version of any content it syncs (per [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s Versioning Model, which governs content, not plugin code).

## SDK Architectural Contract

Every Connector Plugin SHALL implement the `ConnectorPort` interface, which the SDK defines and every one of the fifteen shared components in [65_Connector_Architecture.md](65_Connector_Architecture.md) depends on rather than any plugin-specific type. This is the direct architectural mechanism realizing Open/Closed and Plugin-Ready from [34_Architecture_Principles.md](34_Architecture_Principles.md): the Synchronization Engine, Delta Detection Engine, Health Monitor, and every other shared component are written once, against the SDK's contract, and never modified when a new connector is added.

### Required Capabilities

Every Connector Plugin, via the SDK contract, SHALL provide:

| Capability | Consumed By |
|---|---|
| Authenticate | Authentication Layer (component 3) |
| Validate Connection | Connector Configuration Manager (component 13), realizing FR-CN-002 |
| Full Sync | Synchronization Engine (component 4) |
| Incremental Sync | Synchronization Engine, Delta Detection Engine (components 4, 10) |
| Report Health | Health Monitor (component 12) |
| Extract Metadata | Metadata Extraction Engine (component 6), per [69_Metadata_Extraction.md](69_Metadata_Extraction.md) |
| Synchronize Permissions | Permission Synchronization Engine (component 7), per [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md) |
| Fetch Document | Document Fetch Engine (component 8) |
| Handle Webhook (optional, where the source system supports push notifications) | Webhook Handler (component 9) |
| Report Version | Connector Configuration Manager, per the Versioning Model below |

A Connector Plugin lacking a genuinely applicable capability (e.g., a Filesystem connector has no meaningful "Authenticate" beyond filesystem access permissions) SHALL provide a no-op implementation documenting why, rather than omitting the method — preserving a uniform contract every shared component can rely on without conditional logic per connector.

## Connector Versioning and Upgrade Support

**Binding rule:** Connector Plugins SHALL support future upgrades without requiring a redesign of the shared connector subsystem components, directly implementing FR-CN-012's acceptance criteria and Design Principle 13/10 from [65_Connector_Architecture.md](65_Connector_Architecture.md).

- Every Connector Plugin carries a **Connector Version** (semantic versioning, Deferred to Architecture for the exact scheme), independent of the CES specification version and independent of the core platform's own release version.
- A Connector Plugin version upgrade (e.g., adapting to a source system's breaking API change) is deployed as a replacement implementation behind the same `ConnectorPort` contract — the shared components (Synchronization Engine, Health Monitor, etc.) require no change.
- Where a new Connector Plugin version changes its metadata-extraction behavior or delta-detection semantics in a way that could affect already-synced content's interpretation, the Connector Configuration Manager SHALL record which version synced which content (extending the Provenance model's `CONNECTOR_SYNC` mechanism from [47_Data_Governance.md](47_Data_Governance.md) with the specific `SyncRun`'s Connector Version), enabling later reconciliation if a version-specific defect is discovered.
- The SDK contract itself is versioned independently of individual plugins — an SDK contract version bump (e.g., adding a new required capability) is a breaking change requiring every existing plugin to be updated, and follows the same API Versioning Strategy discipline as FR-AP-006, applied internally to the plugin ecosystem rather than externally to API consumers.

## Independent Configurability

Per Design Principle 2 in [65_Connector_Architecture.md](65_Connector_Architecture.md), every Connector Plugin instance (a specific configured connection, e.g., "Engineering Team's Slack workspace") is independently configurable through the Connector Configuration Manager, without any configuration change affecting another connector instance of the same or a different plugin — this is the same isolation guarantee already established for tenant data in [46_Multi_Tenancy.md](46_Multi_Tenancy.md), applied to connector configuration state.

## Responsibilities

- Every new Connector Plugin proposed in a later phase must implement the full `ConnectorPort` contract (with documented no-ops where genuinely inapplicable) before being added to the catalog in [65_Connector_Architecture.md](65_Connector_Architecture.md).
- A proposed SDK contract change must be evaluated for backward compatibility with every existing Connector Plugin before being accepted, per the same discipline as [09_Governance.md](09_Governance.md)'s breaking-change review process.

## Constraints

- This document does not specify the SDK's implementation language binding, package structure, or method signatures — Deferred to Architecture, consistent with [33_Directory_Structure.md](33_Directory_Structure.md)'s `connectors/framework/` location housing this contract.
- Connector Version is distinct from, and shall not be confused with, the Base Entity Envelope's per-row optimistic-locking `Version` field ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)) or the content Versioning Model — three distinct "version" concepts exist in this specification, each scoped to what it versions.

## Future Considerations

- A certified third-party/partner connector program (per [12_Future_Expansion.md](12_Future_Expansion.md)) would build directly on this SDK contract, with the addition of a certification/review process for externally authored plugins before catalog inclusion.

## Acceptance Criteria

- [ ] The SDK's architectural contract is defined with all ten required capabilities and their consuming shared component.
- [ ] Connector Versioning is defined as independent of platform release versioning and content versioning, with a clear upgrade mechanism.
- [ ] Independent configurability is explicitly stated as an isolation guarantee between connector instances.
