# 69 — Metadata Extraction

## Purpose

This document defines the fifteen metadata fields the Metadata Extraction Engine extracts from source content where available, and maps each to its home in the Canonical Data Model. It elaborates FR-CN-010 (Connector Metadata Extraction) and FR-KI-007 (Ingestion Metadata Extraction) from [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Scope

This document covers metadata field definitions and their storage mapping. It does not cover the derived/enrichment metadata produced later in the Knowledge Processing pipeline (topics, keywords, classifications — see FR-KP-006/007 and [45_Data_Lifecycle.md](45_Data_Lifecycle.md)'s Metadata Enrichment stage), which is a distinct, later pipeline stage from this connector-time structural extraction.

## Definitions

- **Structural Metadata** — Metadata present in or directly derivable from the source system at sync time, as opposed to metadata computed later by Cerebrum's own processing (enrichment metadata).
- **"Where available"** — Not every source system exposes every field below; a connector extracts what its source system provides and leaves the remainder null, never fabricating a value.

## Metadata Fields

The Metadata Extraction Engine SHALL extract the following fifteen fields where available:

| Field | Description | Canonical Data Model Mapping |
|---|---|---|
| Title | The item's human-readable name. | `Document.title` ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) |
| Author | Who created the item. | `Document`/Base Entity Envelope `Created By` ([44_Global_Entity_Model.md](44_Global_Entity_Model.md)) |
| Owner | Who is currently responsible for the item, where distinct from Author (per [68_Synchronization_Architecture.md](68_Synchronization_Architecture.md)'s Permission Synchronization Ownership element). | Feeds FR-ED-004 Knowledge Ownership Attribution |
| Department | The organizational department associated with the item, where the source system models this. | Feeds Team/User Management Domain association |
| Project | The project associated with the item. | `Project` entity linkage ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) |
| Created Date | When the item was originally created at the source. | Base Entity Envelope `Creation Timestamp`, distinct from Cerebrum's own ingestion timestamp |
| Modified Date | When the item was last changed at the source. | Base Entity Envelope `Last Modified Timestamp` |
| Language | The item's primary language. | `Document.language`, also feeding FR-KI-008 |
| Tags | Source-system-native tags applied to the item. | Feeds FR-DM-004 Tagging (as system-derived tags, distinguished from manually applied Cerebrum tags) |
| Labels | Source-system-native labels (a distinct concept from tags in some source systems, e.g., Gmail labels vs. Slack tags). | Same mapping as Tags, kept as a distinct field where the source system distinguishes them |
| Category | A source-system-native categorization. | Feeds FR-KP-006 Metadata Enrichment's classification, seeded by this structural signal |
| Version | The source-system-native version identifier, where the source system exposes one (e.g., a SharePoint document version number). | Feeds [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s Versioning Model as an input signal, distinct from Cerebrum's own Major/Minor/Patch scheme |
| File Type | The document's format (PDF, DOCX, etc.). | `Document.file_type` |
| Source System | Which connector category produced this item. | `Knowledge Source` entity, `Connector` reference ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) |

## Extraction Timing and Ownership

Metadata Extraction occurs at Connector Lifecycle stage 5 (Metadata Discovery, [67_Connector_Lifecycle.md](67_Connector_Lifecycle.md)) for the initial lightweight pass, and again per-item during Document Fetch (component 8, [65_Connector_Architecture.md](65_Connector_Architecture.md)) as each item's full content is retrieved — the Metadata Discovery pass may surface a subset of these fields (e.g., Title, File Type) sufficient for sync planning, while the full field set is captured at fetch time and handed to Knowledge Ingestion's own FR-KI-007 stage.

## Responsibilities

- Every Connector Plugin must map its source system's native metadata fields to this fifteen-field structure at implementation time, documenting which fields its source system does not support (rather than silently omitting the mapping).
- A field left null due to source-system non-support must be distinguishable, in the data model, from a field that failed to extract due to an error — the former is expected and benign; the latter is an Ingestion Failure Recovery case (FR-KI-011).

## Constraints

- This document does not specify the per-connector field-mapping table (e.g., exactly which Slack API field maps to "Owner") — Deferred to Architecture, per-connector.
- This document does not cover enrichment metadata computed by Cerebrum's own processing pipeline after ingestion — see FR-KP-006/007 in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Future Considerations

- As new connector categories are added, source-system-specific metadata beyond this common fifteen-field set (e.g., a Jira issue's Status field) should be captured as connector-specific extended metadata, additive to rather than replacing this common structure, consistent with FR-CN-010's Future Expansion note about "extraction of source-system-specific metadata unique to a given connector category."

## Acceptance Criteria

- [ ] All fifteen metadata fields from the governing specification are defined with a Canonical Data Model mapping.
- [ ] The "where available" qualifier is explicitly addressed — no field is treated as always-present.
- [ ] The distinction between structural (connector-time) and enrichment (processing-time) metadata is explicit, avoiding overlap with FR-KP-006/007.
