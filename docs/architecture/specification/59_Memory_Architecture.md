# 59 — Memory Architecture

## Purpose

This document defines the Memory AI Subsystem Layer's architecture: the categories of contextual memory it maintains, the operations it supports, and the binding rule that memory augments but never replaces enterprise knowledge. It elaborates the Enterprise Memory Domain from [35_Domain_Architecture.md](35_Domain_Architecture.md) and FR-EM-001 through FR-EM-010 from [20_Functional_Requirements.md](20_Functional_Requirements.md) specifically as they serve the AI Request Lifecycle's Memory Layer role (stage input to Context Assembly, [54_Context_Assembly.md](54_Context_Assembly.md)).

## Scope

This document covers the AI-facing role of Memory: what it supplies to retrieval and reasoning, and the operational rules governing its lifecycle. It does not redefine the Enterprise Memory Domain's full data architecture (see [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md), [45_Data_Lifecycle.md](45_Data_Lifecycle.md)) or its eight durable-memory categories from Part 2 (Conversation, Decision, Architecture, Project, Employee, Meeting, Customer, Policy Memory) beyond what is needed to distinguish them from this document's AI-specific memory categories.

## Definitions

- **Memory Freshness** — Whether a memory record's content is still considered current and safe to inject into a prompt, evaluated at request time, distinct from the Enterprise Memory Domain's Freshness Signal (FR-EM-010) which this concept directly reuses.
- **Contextual Memory** — Information that improves the quality of a *future* interaction without itself being organizational fact — the distinction this document exists to enforce.

## Binding Principle: Memory Augments, Never Replaces

The Memory Layer SHALL augment retrieval. Memory SHALL NEVER replace enterprise knowledge. This is the single most important architectural rule in this document, and it resolves a risk specific to conversational AI systems: without this rule, a system might "remember" a prior answer and repeat it on a later query without re-verifying it against current enterprise knowledge — silently allowing stale or since-corrected information to persist as if it were still true. Cerebrum's architecture prevents this structurally: Memory Layer content is always supplementary context alongside a fresh Retrieval pass ([52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)), never a substitute for it. A query is never answered from memory alone.

Memory SHALL contain only contextual information useful for improving future interactions — not a second, competing copy of organizational fact. Where a memory category's content overlaps with an Enterprise Memory Domain category from Part 2 (e.g., this layer's "Decision Context" versus the domain's "Decision Memory"), the domain's PostgreSQL-owned record ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) remains the single authoritative source — this layer's "context" is a lightweight, request-scoped pointer/summary into that source, never an independent copy that could drift out of sync with it.

## Memory Categories

The Memory Layer SHALL maintain the following nine categories, each scoped as described:

| Category | Scope | Relationship to Part 2 Enterprise Memory Domain |
|---|---|---|
| Conversation Memory | The current and recent conversation's turns and their outcomes. | Directly backed by FR-EM-001 Conversation Memory. |
| User Preference Memory | A user's stated or inferred preferences (e.g., preferred response format, frequently asked topics). | New — not a Part 2 Enterprise Memory category; owned by User Management Domain's `UserPreferenceSet` ([43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)) for durable preferences, with a request-scoped working copy here. |
| Workspace Context | The requesting user's workspace scope and its salient characteristics (active projects, recent activity). | Derived from Workspace Domain state, not a standalone memory record. |
| Project Context | Relevant Project Memory for a query scoped to a known project. | Directly backed by FR-EM-004 Project Memory. |
| Decision Context | Relevant Decision Memory for a query touching organizational decisions. | Directly backed by FR-EM-002 Decision Memory. |
| Meeting Context | Relevant Meeting Memory for a query touching meeting-derived knowledge. | Directly backed by FR-EM-006 Meeting Memory. |
| Architecture Context | Relevant Architecture Memory for a technical query. | Directly backed by FR-EM-003 Architecture Memory. |
| Task Context | The user's current in-progress task, if inferable from conversation or connector activity (e.g., an open Jira ticket referenced earlier in conversation). | New — request-scoped, not a durable Part 2 memory category. |
| Domain Context | Organization-specific terminology, conventions, and structure relevant to interpreting the query (feeds Query Rewriting's Company Terminology technique, [52_Retrieval_Architecture.md](52_Retrieval_Architecture.md)). | New — derived from aggregate patterns across Enterprise Memory categories, not a standalone record. |

## Memory Operations

The Memory Layer SHALL support the following seven operations:

| Operation | Description |
|---|---|
| Creation | A new memory entry is created from conversation activity, explicit user input, or inferred context. |
| Retrieval | Memory relevant to the current query is fetched for Context Assembly (operation 5 in [54_Context_Assembly.md](54_Context_Assembly.md)). |
| Updating | An existing memory entry is refreshed as new, relevant activity occurs. |
| Expiration | A memory entry's freshness window elapses; see Memory Freshness below. |
| Archiving | A memory entry is retained but excluded from active retrieval, mirroring the Archived lifecycle state pattern in [45_Data_Lifecycle.md](45_Data_Lifecycle.md). |
| Deletion | A memory entry is removed, following the same Soft Delete Strategy as any other entity ([47_Data_Governance.md](47_Data_Governance.md)). |
| Permission Validation | Every memory retrieval is filtered by the requesting user's permissions, per the same rule as every other content source reaching Context Assembly. |

## Memory Freshness

**Binding rule:** Memory freshness SHALL be evaluated before every AI request. Expired memory SHALL NOT be injected into prompts.

Freshness evaluation reuses the Enterprise Memory Domain's Staleness/Freshness Signal mechanism (FR-EM-009/FR-EM-010) where a memory category maps to a durable Enterprise Memory record, and applies an analogous, request-scoped freshness check for the new categories introduced in this document (User Preference, Workspace/Task/Domain Context) — a fixed or configurable time-to-live per category, Deferred to Architecture for the specific durations, configured via [62_AI_Governance.md](62_AI_Governance.md).

This rule exists to prevent a specific failure mode: a long-running conversation referencing a project's status early on, where that status has since changed — without freshness evaluation, a later turn could inject the stale early-conversation memory into the prompt, causing the AI to reason from outdated context even though current data is available via Retrieval. Freshness evaluation ensures memory content is either confirmed current or excluded, never assumed current by default.

## Responsibilities

- Every new memory category proposed in a later phase must be classified as either backed by an existing Enterprise Memory Domain record (Part 2) or a new, request-scoped context type — introducing a new durable memory store that duplicates Enterprise Memory Domain data requires an ADR justifying why the existing domain's record is insufficient.
- Memory Freshness evaluation is mandatory on every request; a code path that injects memory into Context Assembly without a freshness check is a review-blocking finding.

## Constraints

- This document does not specify the exact freshness time-to-live per category — Deferred to Architecture, configured via [62_AI_Governance.md](62_AI_Governance.md).
- This document does not introduce new entity categories beyond the 30 in [44_Global_Entity_Model.md](44_Global_Entity_Model.md) — new categories here (User Preference, Workspace/Task/Domain Context) are request-scoped working representations, not new persisted entity types.

## Future Considerations

- As Task Context and Domain Context inference matures, their accuracy should become a tracked Evaluation Layer metric ([61_AI_Evaluation.md](61_AI_Evaluation.md)), since incorrect inference here (e.g., misidentifying the user's current task) could degrade retrieval precision without an obvious failure signal.

## Acceptance Criteria

- [ ] The "augments, never replaces" binding principle is stated clearly with the specific failure mode it prevents.
- [ ] All nine memory categories from the governing specification are defined and reconciled with Part 2's Enterprise Memory Domain categories.
- [ ] All seven memory operations from the governing specification are defined.
- [ ] Memory Freshness evaluation is stated as mandatory on every request, with expired memory exclusion stated as binding.
