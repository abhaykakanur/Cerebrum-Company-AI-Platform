# 57 — Citation Engine

## Purpose

This document defines the Citation AI Subsystem Layer's architecture: the sources a citation may reference, and the fields every citation must carry. It elaborates FR-CT-001 through FR-CT-004 from [20_Functional_Requirements.md](20_Functional_Requirements.md) and the Citation Domain architecture from [35_Domain_Architecture.md](35_Domain_Architecture.md).

## Scope

This document covers citation source types and citation field structure. It does not cover confidence scoring (see [58_Confidence_Engine.md](58_Confidence_Engine.md), which consumes citation verification outcomes) or the Citation entity's data model (see [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)).

## Definitions

- **Citation Source** — The category of enterprise content a citation may point to.
- **Citation Verification** — Confirming, per FR-CT-003, that a cited source actually supports the claim it is attached to.

## Binding Rule

Every enterprise response SHALL attempt to provide citations, per the AI Design Philosophy's fourth rule ([50_AI_Architecture.md](50_AI_Architecture.md)). "Attempt" acknowledges that a purely conversational exchange (e.g., a clarifying question back to the user) may have no citable claim — but any response containing a factual, organizational claim SHALL have a citation for that claim, with no exception.

## Citation Sources

A citation SHALL reference exactly one of the following source categories, each mapped to its authoritative representation per [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md):

| Citation Source | Underlying Entity Category | Connector Category (if applicable) |
|---|---|---|
| Documents | Document / Document Version / Chunk | Any |
| Meetings | Meeting | Meeting Intelligence source |
| Policies | Policy (specialized Document) | Any document connector |
| Emails | Document (ingested via Gmail/Outlook Mail connector) | Gmail, Outlook Mail |
| Slack Messages | Document (ingested via Slack connector) | Slack |
| GitHub Repositories | Document (code content) | GitHub |
| Issues | Document (specialized, ticket-shaped content) | Jira, Linear, GitHub, GitLab |
| Pull Requests | Document (specialized, code-review-shaped content) | GitHub, GitLab |
| Knowledge Graph Nodes | Knowledge Entity | N/A — internally derived |
| Confluence Pages | Document | Confluence |
| Notion Pages | Document | Notion |
| Architecture Records | Decision (Architecture Memory subset, FR-EM-003) | N/A — internally derived |

This list confirms that every Citation Source ultimately resolves to one of the 30 entity categories in [44_Global_Entity_Model.md](44_Global_Entity_Model.md) — no new entity category is introduced by the Citation Engine; it is a reference layer over the existing canonical model.

## Required Citation Fields

Every citation SHALL include the following seven fields, extending the `Citation` entity's structure from [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md):

| Field | Purpose |
|---|---|
| Source | The Citation Source category (from the table above). |
| Title | A human-readable identifier for the cited item (document title, meeting name, PR title). |
| Timestamp | When the cited content was created or last modified, supporting freshness assessment (FR-EM-010). |
| Author | Who authored or is attributed to the cited content, where known — nullable for connector-synced content with no clear individual author (per [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s Document entry). |
| Location | The specific position within the source (page, section, message timestamp, line range) — not merely "this document," but the precise passage, directly supporting FR-CT-002's navigable citation requirement. |
| Confidence | The Citation Verification outcome's confidence that this source genuinely supports the claim, distinct from the response's overall Confidence Level ([58_Confidence_Engine.md](58_Confidence_Engine.md)) — a per-citation confidence, not only a per-response one. |
| Permission Validation | Confirmation that the requesting user is authorized to view the cited source, re-checked at citation-display time per FR-CT-002's requirement that an unauthorized user never receives a navigable link to content they cannot see. |

## Responsibilities

- Every new connector category added per FR-CN-011 must be mapped to an existing Citation Source category (most will fall under "Documents" with connector-specific sub-typing) before its content is eligible for citation.
- Permission Validation on every citation is non-negotiable and re-checked at citation-display time, not only at retrieval time — content permissions can change between when a response was generated and when a user views a previously generated response (e.g., in Conversation History, FR-CV-003).

## Constraints

- This document does not specify the citation's display format (inline marker, footnote, hyperlink) — a presentation concern Deferred to Architecture.
- This document does not specify how Citation Verification's confidence score is computed — see [58_Confidence_Engine.md](58_Confidence_Engine.md) for the broader confidence model this feeds into.

## Future Considerations

- As new connector categories are added (per [12_Future_Expansion.md](12_Future_Expansion.md)), the Citation Sources table should be extended with their mapping, preserving the rule that every source resolves to an existing entity category rather than requiring a new one.

## Acceptance Criteria

- [ ] All twelve citation sources from the governing specification are defined with their underlying entity category.
- [ ] All seven required citation fields from the governing specification are defined with their purpose.
- [ ] Permission Validation is stated as re-checked at display time, not assumed valid from retrieval time.
