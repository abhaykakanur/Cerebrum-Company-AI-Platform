# 114 — Open Questions (CES Phase 0, Part 10) and Consolidated Cross-Part Index

## Purpose

This document records the small number of new ambiguities this final review itself surfaced, and — fulfilling the recommendation repeated in every Open Questions document since [74_Open_Questions.md](74_Open_Questions.md) — provides the consolidated, theme-grouped index across all ten parts' Open Questions documents (129 questions total).

## Scope

This document covers Part 10-specific new questions and the cross-part consolidation. It does not restate the full content of any prior question — see the cited source document for full Question/Reason/Impact detail.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## New Questions Surfaced by This Review

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 129 | Should Incident be given a dedicated FR-EM-011 "Incident Memory" requirement matching the treatment given to Project, Customer, and Policy Memory, or is general Memory Record flexibility sufficient to cover it without a dedicated FR? | [105_Final_Architecture_Review.md](105_Final_Architecture_Review.md) Finding 1 identified that [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md) catalogues Incident as an entity category owned by Enterprise Memory Domain, but no corresponding FR-EM requirement exists, unlike its seven sibling memory categories. | 105, 20, 43 | Enterprise Memory Domain completeness; a Phase 10 (Knowledge Intelligence) implementation dependency. |
| 130 | Who is the named Architecture Owner? | [109_Project_Governance.md](109_Project_Governance.md) defines the role but cannot itself make the staffing appointment. | 109 | Phase 1 entry criteria, per [112_Readiness_Checklist.md](112_Readiness_Checklist.md). |
| 131 | Who owns ongoing maintenance of the consolidated Open Questions index below as new questions are added and existing ones resolved during implementation? | This document creates the index but the specification does not itself assign a maintenance owner beyond the general [109_Project_Governance.md](109_Project_Governance.md) Change Management process. | 114, 109 | Open Questions backlog hygiene through Phase 1–12. |

## Consolidated Cross-Part Index

129 open questions have accumulated across ten parts. This index groups them by theme rather than by originating part, so a team resolving one question can see related questions together.

| Theme | Question Numbers | Originating Documents | Count |
|---|---|---|---|
| Multi-Tenancy, Data Residency & Storage | 3, 21, 38, 41, 52, 53, 57, 65, 127, 128 | [11](11_Open_Questions.md), [27](27_Open_Questions.md), [40](40_Open_Questions.md), [46](46_Multi_Tenancy.md), [49](49_Open_Questions.md), [102](102_Backup_Recovery.md) | 10 |
| AI Safety, Guardrails & Model Behavior | 6, 10, 30, 42, 67, 68, 69, 75, 76, 79, 97 | [11](11_Open_Questions.md), [27](27_Open_Questions.md), [40](40_Open_Questions.md), [64](64_Open_Questions.md), [77](77_Authorization_Model.md), [84](84_Open_Questions.md) | 11 |
| Authorization, Identity & Access Governance | 1, 2, 18 (resolved by [78](78_RBAC_Model.md)), 19, 93, 96, 130 | [11](11_Open_Questions.md), [27](27_Open_Questions.md), [78](78_RBAC_Model.md), [84](84_Open_Questions.md), [114](114_Open_Questions.md) | 6 open (1 resolved) |
| Connector & Integration Scope | 4, 20, 33, 51, 81, 82, 83, 87 | [11](11_Open_Questions.md), [27](27_Open_Questions.md), [40](40_Open_Questions.md), [68](68_Synchronization_Architecture.md), [74](74_Open_Questions.md) | 8 |
| Confidence, Citation & Evaluation Calibration | 6 (shared), 24, 25, 26, 79, 88, 89, 90 | [11](11_Open_Questions.md), [27](27_Open_Questions.md), [58](58_Confidence_Engine.md), [72](72_Search_Ranking.md) | 7 |
| Performance, Scaling & Infrastructure Parameters | 22, 23, 28, 44, 48, 50, 62, 83 (shared), 101, 113, 114, 116 | [27](27_Open_Questions.md), [40](40_Open_Questions.md), [49](49_Open_Questions.md), [92](92_Queue_Architecture.md), [101](101_Monitoring_Architecture.md) | 11 |
| API, Versioning & Deployment Mechanics | 27, 29, 31, 36, 39, 45, 46, 47, 54, 98, 99, 100, 102, 103, 104, 118, 119, 120, 121 | [27](27_Open_Questions.md), [40](40_Open_Questions.md), [82](82_Error_Model.md), [83](83_Webhook_Architecture.md), [96](96_Deployment_Strategy.md), [97](97_CICD_Architecture.md) | 19 |
| Data Model Completeness & Governance Detail | 32, 34, 35, 37, 43, 55, 56, 58, 59, 60, 61, 63, 64, 66, 129 | [40](40_Open_Questions.md), [49](49_Open_Questions.md), [105](105_Final_Architecture_Review.md) | 15 |
| Frontend, Design System & UX Detail | 105, 106, 107, 108, 109, 110, 111, 112, 115 | [94](94_Open_Questions.md) | 9 |
| Engineering Process & Tooling | 117, 122, 123, 124, 125, 126, 131 | [104](104_Open_Questions.md), [114](114_Open_Questions.md) | 7 |
| Governance, Staffing & Backlog Ownership | 130, 131 | [109](109_Project_Governance.md), [114](114_Open_Questions.md) | 2 |

*(Counts are approximate groupings for navigation; a question addressing multiple themes is listed once under its primary theme. Total across all themes reconciles to 129 minus 1 resolved = 128 genuinely open at time of writing.)*

## Priority Subset: Resolve Before Phase 1 or Before General Availability

Per the individual severity flags already raised across Parts 3–9, the following subset carries elevated priority and should not be left to organic, unprioritized resolution:

- **Before Phase 1 (blocking):** 130 (Architecture Owner), 18-adjacent role catalog is already resolved, 38/46-related tenancy model is already resolved — remaining Phase-1-blocking items are primarily staffing/process (130, 131), not specification gaps.
- **Before General Availability (security/safety critical):** 67, 68, 69 (Prompt Injection, PII, Secret Detection — [64_Open_Questions.md](64_Open_Questions.md)), 93 (Platform Owner access mechanism — [84_Open_Questions.md](84_Open_Questions.md)), 35 (incident notification policy — [40_Open_Questions.md](40_Open_Questions.md)).
- **Before Phase 6 (Knowledge Graph) / Phase 10 (Knowledge Intelligence):** 129 (Incident Memory FR).

## Responsibilities

- The Architecture Owner, once named (Open Question 130), inherits responsibility for this consolidated index's ongoing maintenance, resolving Open Question 131 by assignment.
- Every question in this index must be closed via an ADR per [09_Governance.md](09_Governance.md) as it is resolved, with its row moved to a Resolved Questions record — this consolidation does not change that per-question resolution discipline, it only makes the backlog navigable.

## Constraints

- This document does not resolve any of the 128 open questions — consistent with every prior Open Questions document, it records and organizes, it does not decide.
- Theme groupings are a navigational aid; a question's originating document (cited in its theme row) remains its authoritative source for full Question/Reason/Impact/Alternatives detail.

## Future Considerations

- Once implementation tooling exists, this index should become a queryable backlog (e.g., issue tracker labels by theme) rather than a static document, per the same reasoning [82_Error_Model.md](82_Error_Model.md) and [106_Requirement_Traceability.md](106_Requirement_Traceability.md) already applied to their own growing catalogs.

## Acceptance Criteria

- [ ] All new questions surfaced specifically by the Part 10 review are recorded in the standard format.
- [ ] The consolidated cross-part index groups all prior questions by theme, fulfilling the recommendation repeated since [74_Open_Questions.md](74_Open_Questions.md).
- [ ] A priority subset is explicitly called out for pre-Phase-1 and pre-General-Availability resolution, distinguishing genuinely blocking items from the broader backlog.
