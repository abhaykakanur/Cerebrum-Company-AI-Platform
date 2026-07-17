# 25 — Acceptance Criteria (Verification Checklist)

## Purpose

This document consolidates every requirement's acceptance criteria from [20_Functional_Requirements.md](20_Functional_Requirements.md) into a single, condensed, testable checklist suitable for QA planning and verification tracking. Where the source requirement lists multiple acceptance criteria, this document condenses them into one primary, testable verification statement per requirement; the full criteria set remains authoritative in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Scope

This document covers verification statements only. It is a QA-facing derivative of [20_Functional_Requirements.md](20_Functional_Requirements.md), not an independent source of requirements. Where this document and [20_Functional_Requirements.md](20_Functional_Requirements.md) conflict, the latter governs.

## Definitions

- **Verification Statement** — A single, condensed, testable sentence confirming whether a requirement's core behavior is present, derived from its full acceptance criteria in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## How to Use This Checklist

Each row names a requirement and the primary condition that must hold true to consider it verified. A checked box here is not sufficient sign-off on its own — full sign-off requires validating every acceptance criterion listed under the requirement in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Verification Checklist

### Identity / Workspace / Organization
- [ ] FR-ID-001 — Duplicate organization identifiers are rejected; a new organization receives a unique immutable ID.
- [ ] FR-ID-002 — A workspace can be created under an organization and inherits organization defaults.
- [ ] FR-ID-003 — Organization profile fields are editable only by authorized actors.
- [ ] FR-ID-004 — Workspace profile changes are visible to all members without re-login.
- [ ] FR-ID-005 — Uploaded branding applies consistently across workspaces.
- [ ] FR-WS-001 — Invalid workspace lifecycle transitions (e.g., Deleted → Active) are rejected.
- [ ] FR-WS-002 — Workspace setting changes take effect without redeployment.
- [ ] FR-WS-003 — Removing the last workspace owner is blocked absent a completed transfer.
- [ ] FR-WS-004 — Ownership transfer requires confirmation and notifies the new owner.
- [ ] FR-WS-005 — Deletion requires explicit confirmation and enters a recoverable grace period.
- [ ] FR-WS-006 — Archived workspace is read-only and hidden from default views but remains searchable to prior members.
- [ ] FR-OR-001 — Suspension blocks logins/ingestion while preserving data.
- [ ] FR-OR-002 — A user sees only workspaces they are authorized to access.
- [ ] FR-OR-003 — A workspace-level override is not overwritten by a later organization-level change.

### User Management
- [ ] FR-UM-001 — Duplicate email registration within an organization is rejected.
- [ ] FR-UM-002 — Expired or revoked invitations cannot be accepted.
- [ ] FR-UM-003 — An inactive (unverified) user cannot access organizational knowledge.
- [ ] FR-UM-004 — Deactivation immediately invalidates active sessions; prior contributions remain attributed.
- [ ] FR-UM-005 — A suspended user cannot authenticate; suspension is independently auditable from deactivation.
- [ ] FR-UM-006 — A soft-deleted user no longer appears in active listings; authored content remains subject to normal retention.
- [ ] FR-UM-007 — Preference changes take effect on next interaction without re-login.
- [ ] FR-UM-008 — Team/manager relationship changes propagate to expertise mapping without manual reprocessing.

### Authentication
- [ ] FR-AUTH-001 — Incorrect credentials are rejected without revealing which field was wrong.
- [ ] FR-AUTH-002 — A reset link is single-use and time-limited.
- [ ] FR-AUTH-003 — A magic link authenticates exactly once and expires if unused.
- [ ] FR-AUTH-004 — The identity model supports an external-provider-linked identity distinct from password login.
- [ ] FR-AUTH-005 — The identity model supports organization-level SSO configuration.
- [ ] FR-AUTH-006 — The identity model supports an optional second verification factor.
- [ ] FR-AUTH-007 — A user can view and revoke their own active sessions.
- [ ] FR-AUTH-008 — A trusted-device designation expires after a defined period.
- [ ] FR-AUTH-009 — Recovery requires an alternate verification channel and is fully audited.

### Authorization
- [ ] FR-AUTZ-001 — A user's effective permissions equal the union of their assigned roles' permissions.
- [ ] FR-AUTZ-002 — An explicit resource-level restriction overrides inherited permission for that resource only.
- [ ] FR-AUTZ-003 — No response leaks content or existence of a resource the user is unauthorized for.
- [ ] FR-AUTZ-004 — A workspace-only admin cannot modify organization-level settings or other workspaces.
- [ ] FR-AUTZ-005 — A newly created role has zero permissions until explicitly granted.
- [ ] FR-AUTZ-006 — Every permission change produces an immutable, queryable audit record.

### Connector
- [ ] FR-CN-001 — A connector defaults to read-only, minimum-necessary scope.
- [ ] FR-CN-002 — A connector cannot be enabled until validation succeeds, with an actionable failure reason.
- [ ] FR-CN-003 — A full sync retrieves all in-scope content and can be manually re-triggered.
- [ ] FR-CN-004 — A failed incremental sync does not advance the checkpoint.
- [ ] FR-CN-005 — A manual trigger during an in-progress sync is queued, not run concurrently.
- [ ] FR-CN-006 — A connector transitioning to Failed triggers a notification.
- [ ] FR-CN-007 — Transient failures retry with backoff; non-transient failures escalate immediately.
- [ ] FR-CN-008 — Conflict resolution is deterministic and reproducible from identical inputs.
- [ ] FR-CN-009 — Every sync attempt, regardless of outcome, produces a queryable log entry.
- [ ] FR-CN-010 — Every synced item retains its source-native ID, author, and last-modified timestamp.
- [ ] FR-CN-011 — Each of the 23 listed connector categories has an implementation satisfying FR-CN-001–010.
- [ ] FR-CN-012 — A new connector integrates via the defined interface without modifying downstream domain data models.

### Knowledge Ingestion
- [ ] FR-KI-001 — An uploaded supported-type file enters the ingestion pipeline and is attributed to the uploader.
- [ ] FR-KI-002 — Partial failures within a bulk upload are reported per-item, not as one aggregate failure.
- [ ] FR-KI-003 — Connector-sourced content passes through the same pipeline stages as manual upload.
- [ ] FR-KI-004 — Unchanged content is not reprocessed on an incremental sync delta.
- [ ] FR-KI-005 — Exact duplicates are not re-indexed as separate items.
- [ ] FR-KI-006 — A re-synced item with the same source ID is linked as a new version, not a new item.
- [ ] FR-KI-007 — Missing/malformed metadata is flagged for review, not silently dropped.
- [ ] FR-KI-008 — Detected language is recorded as item metadata.
- [ ] FR-KI-009 — Image-based/scanned content is automatically routed to OCR.
- [ ] FR-KI-010 — Normalization preserves headings/lists/tables across all supported source formats.
- [ ] FR-KI-011 — One item's ingestion failure does not halt processing of the rest of the batch.
- [ ] FR-KI-012 — Every ingestion run produces a summary report.

### Knowledge Processing
- [ ] FR-KP-001 — Extracted text preserves reading order for standard layouts.
- [ ] FR-KP-002 — Tables are extracted with row/column structure preserved, not flattened.
- [ ] FR-KP-003 — OCR output includes a per-region confidence score.
- [ ] FR-KP-004 — Text is normalized to a consistent encoding/whitespace convention prior to chunking.
- [ ] FR-KP-005 — Chunks respect semantic boundaries where the source format provides them and retain a source link.
- [ ] FR-KP-006 — Every processed item receives at least one derived classification.
- [ ] FR-KP-007 — Extracted keywords/topics are stored as searchable, reasonably consistent metadata.
- [ ] FR-KP-008 — Extracted entities are typed and linked to source content; relationships specify type and related entities.
- [ ] FR-KP-009 — Every indexed chunk has an embedding before appearing in semantic search.
- [ ] FR-KP-010 — Items below the quality bar are indexed in a visibly flagged state, not excluded silently.

### Knowledge Storage
- [ ] FR-KS-001 — Stored content is retrievable after a routine service restart.
- [ ] FR-KS-002 — Metadata is queryable independently of full-content retrieval.
- [ ] FR-KS-003 — Every version of a versioned item is individually retrievable.
- [ ] FR-KS-004 — Content reaching retention limit is archived/flagged per policy, not immediately purged without defined behavior.
- [ ] FR-KS-005 — Archived content is excluded from default search but retrievable via explicit query; restore returns full active status.
- [ ] FR-KS-006 — Soft-deleted content is immediately excluded from search/retrieval/reasoning; permanent deletion removes derivatives.
- [ ] FR-KS-007 — Scheduled integrity checks produce a report of detected inconsistencies.

### Knowledge Graph
- [ ] FR-KG-001 — A newly identified entity is created with type and source reference; known entities are linked, not duplicated.
- [ ] FR-KG-002 — A relationship links exactly two entities with a typed label and source reference.
- [ ] FR-KG-003 — Merging combines source references without loss and is reversible within a defined window.
- [ ] FR-KG-004 — Likely duplicates are flagged with a stated similarity basis, queued for review.
- [ ] FR-KG-005 — A change to an entity/relationship is timestamped and does not erase prior state.
- [ ] FR-KG-006 — A traversal query returns entities/relationships within a specified depth, filtered by permissions.
- [ ] FR-KG-007 — A timeline view lists source events chronologically with source links, filtered by permissions.
- [ ] FR-KG-008 — Traversal results include node/edge metadata sufficient to render without additional lookups.

### Enterprise Search
- [ ] FR-ES-001 — A keyword query returns matching, permission-filtered content ranked by relevance.
- [ ] FR-ES-002 — A natural-language query returns semantically relevant content without requiring exact keyword overlap.
- [ ] FR-ES-003 — A query returns a single ranked list combining keyword and semantic signals.
- [ ] FR-ES-004 — Metadata filters combine with, rather than replace, relevance ranking.
- [ ] FR-ES-005 — Facet values/counts reflect the current, permission-filtered result set.
- [ ] FR-ES-006 — A graph-scoped query returns content linked to a specified entity within a defined depth.
- [ ] FR-ES-007 — Suggestions appear as the user types and are drawn only from permitted content.
- [ ] FR-ES-008 — Results are returned in deterministic rank order for a given query and permission context.
- [ ] FR-ES-009 — A user can request and receive an explanation naming the signals behind a result's ranking.
- [ ] FR-ES-010 — No search response reveals content or existence of unauthorized resources, across all search methods.

### Retrieval
- [ ] FR-RT-001 — Retrieval returns a permission-filtered candidate set relevant to a reasoning query.
- [ ] FR-RT-002 — Every context element retains a link back to its source item and location.
- [ ] FR-RT-003 — Retrieved candidates are ordered by relevance/reliability before truncation.
- [ ] FR-RT-004 — Near-duplicate chunks are deduplicated while preserving all contributing source references.
- [ ] FR-RT-005 — Assembled context never exceeds the defined token budget; truncation is recorded.
- [ ] FR-RT-006 — No content reaches AI Reasoning without intact source references.
- [ ] FR-RT-007 — Context assembly failing validation is rejected and logged, not passed through with a warning only.

### AI Reasoning
- [ ] FR-AR-001 — Every factual claim traces to a specific context element; no relevant context yields an explicit "unknown."
- [ ] FR-AR-002 — A synthesized multi-source answer cites every contributing source.
- [ ] FR-AR-003 — A cross-document answer explicitly references each contributing document.
- [ ] FR-AR-004 — A complex query is decomposed into sub-questions, each independently retrieved and reasoned over.
- [ ] FR-AR-005 — Every answer undergoes validation against cited sources before being returned.
- [ ] FR-AR-006 — A query with no supporting context produces an explicit "unknown," not a model-only answer.
- [ ] FR-AR-007 — Structured output retains the same citation/grounding requirements as prose.
- [ ] FR-AR-008 — A reasoning trace, on request, distinguishes "considered but unused" from "never retrieved."

### Enterprise Memory
- [ ] FR-EM-001 — A completed conversation is retrievable by the participant and respects source permission boundaries.
- [ ] FR-EM-002 — A recorded decision is retrievable independently of its originating document.
- [ ] FR-EM-003 — Architecture-related decisions are retrievable as a filterable subset of Decision Memory.
- [ ] FR-EM-004 — A project memory view aggregates linked content across source types, permission-filtered per item.
- [ ] FR-EM-005 — A departed employee's authored content and attribution remain retrievable per policy.
- [ ] FR-EM-006 — Meeting memory entries are retrievable independently and as part of related project memory.
- [ ] FR-EM-007 — Customer memory access is scoped to authorized users only.
- [ ] FR-EM-008 — Policy memory entries are flagged current vs. superseded; AI answers prefer the current version.
- [ ] FR-EM-009 — Every retained item has a computed staleness signal based on age and supersession.
- [ ] FR-EM-010 — Every surfaced memory item displays a last-confirmed/last-synced timestamp.

### Conversation
- [ ] FR-CV-001 — A submitted query yields a grounded answer, an "unknown," or a clarifying question.
- [ ] FR-CV-002 — A follow-up query correctly resolves references to prior-turn content within token budget.
- [ ] FR-CV-003 — A user can list, open, resume, and search their own past conversations.
- [ ] FR-CV-004 — Exported conversations retain citations, not stripped of attribution.
- [ ] FR-CV-005 — Suggested follow-ups are grounded in content actually available to the user.

### Citation
- [ ] FR-CT-001 — Every factual claim has an associated citation; uncitable claims are not presented as fact.
- [ ] FR-CT-002 — Selecting a citation navigates to the specific source location, subject to the user's own permission.
- [ ] FR-CT-003 — A citation failing verification causes the claim to be revised, removed, or downgraded before return.
- [ ] FR-CT-004 — Any non-citable portion of an answer is visibly flagged, not silently omitted.

### Confidence
- [ ] FR-CF-001 — Every generated answer has an associated confidence indicator before being returned.
- [ ] FR-CF-002 — Confidence is visibly presented with every answer, not available only on separate request.
- [ ] FR-CF-003 — An answer below the confidence threshold is visibly and unambiguously labeled.
- [ ] FR-CF-004 — A user can provide correctness/usefulness feedback on a specific answer.

### Document Management
- [ ] FR-DM-001 — Download returns the original source format, subject to permission checks.
- [ ] FR-DM-002 — Preview renders extracted content in readable form, subject to permission checks.
- [ ] FR-DM-003 — A user can view version history and open any prior version in preview.
- [ ] FR-DM-004 — A user with edit permission can add/remove tags; manual tags are searchable.
- [ ] FR-DM-005 — Connector-synced folder structure is presented consistently with manual collections.
- [ ] FR-DM-006 — Sharing does not grant access beyond the recipient's existing permissions.
- [ ] FR-DM-007 — An archived document is excluded from default search but retrievable via explicit query.

### Meeting Intelligence
- [ ] FR-MI-001 — A transcript, however sourced, enters the standard ingestion pipeline with meeting metadata captured.
- [ ] FR-MI-002 — Source-provided speaker labels are preserved through ingestion and processing.
- [ ] FR-MI-003 — A summary is generated for every ingested transcript and cites the source transcript.
- [ ] FR-MI-004 — Extracted action items are structured, individually retrievable, and cite their source segment.
- [ ] FR-MI-005 — A meeting-identified decision is recorded with a link to the specific transcript segment.
- [ ] FR-MI-006 — Suggested follow-ups are grounded and distinguished from confirmed action items.
- [ ] FR-MI-007 — Mentioned entities are linked to existing graph entities or create new ones.

### Decision Intelligence
- [ ] FR-DI-001 — A decision record links to at least one source reference, whether auto-extracted or manually entered.
- [ ] FR-DI-002 — A timeline view lists related decisions chronologically with source links.
- [ ] FR-DI-003 — A decision record has a distinct rationale field; absence of rationale is explicitly recorded, not left ambiguous.
- [ ] FR-DI-004 — A decision record lists identified participants linked to user/entity records where confident.
- [ ] FR-DI-005 — A decision record supports multiple independently citable evidence links.
- [ ] FR-DI-006 — A decision record can link to outcome/supersession references; superseded decisions are flagged.

### Expertise Discovery
- [ ] FR-ED-001 — An expert query returns a ranked candidate list with contributing signals exposed.
- [ ] FR-ED-002 — A user's skill/technology map updates from ongoing contributions without manual maintenance.
- [ ] FR-ED-003 — A user's project involvement list stays current as new contributions are ingested.
- [ ] FR-ED-004 — A knowledge area's inferred owner is exposed with its underlying signal disclosed.
- [ ] FR-ED-005 — Expert results indicate current account status; departed employees are labeled, not hidden.

### Analytics
- [ ] FR-AL-001 — Zero-result queries are separately reportable by workspace and time range.
- [ ] FR-AL-002 — Usage analytics are reportable at organization and workspace scope.
- [ ] FR-AL-003 — Coverage and grounding-rate trends are reportable and distinguishable from normal variance.
- [ ] FR-AL-004 — Connector analytics are reportable per connector and aggregated.
- [ ] FR-AL-005 — Latency analytics report percentile distributions, not only averages.
- [ ] FR-AL-006 — Adoption analytics are reportable over a configurable time range.

### Administration
- [ ] FR-AD-001 — An admin can view all in-scope workspaces and perform any authorized lifecycle action.
- [ ] FR-AD-002 — An admin can view, invite, deactivate, and modify roles for in-scope users.
- [ ] FR-AD-003 — An admin can add, configure, monitor, and disable in-scope connectors.
- [ ] FR-AD-004 — A delegated admin can perform only the specific functions granted, auditable and revocable.

### Monitoring
- [ ] FR-MN-001 — Each core subsystem exposes a current health status.
- [ ] FR-MN-002 — An in-progress long-running operation exposes near-real-time processed/remaining/failed counts.
- [ ] FR-MN-003 — A degradation event triggers a notification to designated recipients.
- [ ] FR-MN-004 — The dashboard shows current status and historical uptime trend per subsystem.

### Audit
- [ ] FR-AU-001 — Every audit-relevant action produces an immutable record; records cannot be modified/deleted through normal function.
- [ ] FR-AU-002 — Permission-change history is filterable by user, resource, and time range.
- [ ] FR-AU-003 — Login history is viewable by the user and authorized administrators.
- [ ] FR-AU-004 — Connector activity history is filterable by connector, actor, and time range.
- [ ] FR-AU-005 — Search-history-audit access is itself permission-restricted given its sensitivity.
- [ ] FR-AU-006 — Administrative action history is filterable by actor, action type, and time range.

### Configuration
- [ ] FR-CG-001 — AI configuration changes take effect for subsequent queries without a restart.
- [ ] FR-CG-002 — Search configuration changes take effect for subsequent queries without a restart.
- [ ] FR-CG-003 — A feature flag's state determines capability availability without a code deployment.
- [ ] FR-CG-004 — System settings are discoverable in a single administrative view.

### Security
- [ ] FR-SC-001 — All persisted content, metadata, and credentials are encrypted at rest.
- [ ] FR-SC-002 — No unencrypted channel is used for any inter-component or client-to-system transmission.
- [ ] FR-SC-003 — Secrets are never stored in plaintext in logs, general databases, or version-controlled config.
- [ ] FR-SC-004 — No query/retrieval/reasoning operation can return another organization's data under any input.
- [ ] FR-SC-005 — Known dependency vulnerabilities are tracked with a defined remediation SLA.
- [ ] FR-SC-006 — A defined incident response process exists and is exercised; affected customers are notified per policy.

### Notification
- [ ] FR-NT-001 — A user can view and mark in-app notifications as read, permission-bounded.
- [ ] FR-NT-002 — A user can configure email notification categories except non-optional security ones.
- [ ] FR-NT-003 — A connector's transition to Failed triggers a notification within defined latency.
- [ ] FR-NT-004 — Completion notification includes a summary consistent with ingestion reporting.
- [ ] FR-NT-005 — An uploader is notified once content is indexed or flagged for quality failure.

### API
- [ ] FR-AP-001 — Every primary-interface search/reasoning capability is available via the public API under the same permission enforcement.
- [ ] FR-AP-002 — Every cross-domain dependency is realizable through a defined internal interface.
- [ ] FR-AP-003 — Every Administration Domain capability is available via the administrative API under the same permission enforcement.
- [ ] FR-AP-004 — A new connector can register, report sync results, and surface health entirely through the connector API.
- [ ] FR-AP-005 — Webhook delivery failures retry with backoff and are observable to the registrant.
- [ ] FR-AP-006 — Every public-facing API surface carries an explicit version identifier; breaking changes only ship in a new version.

## Responsibilities

- QA planning in later phases should use this checklist as a starting test-case index, expanding each line into full test cases against the complete acceptance criteria in [20_Functional_Requirements.md](20_Functional_Requirements.md).
- This document must be kept in sync with [20_Functional_Requirements.md](20_Functional_Requirements.md); a new or changed requirement requires a corresponding new or changed line here.

## Constraints

- A checked box here indicates the primary condition was verified, not that every acceptance criterion for that requirement was exhaustively tested. Full sign-off requires the complete criteria set in [20_Functional_Requirements.md](20_Functional_Requirements.md).

## Future Considerations

- As test automation is built in later phases, each line here should link to an automated test identifier (Deferred to Architecture).

## Acceptance Criteria

- [ ] Every requirement in [22_Requirement_Catalog.md](22_Requirement_Catalog.md) has exactly one corresponding line here.
- [ ] Every verification statement is a single, testable sentence, not a restatement of the full requirement description.
