# 94 — Open Questions (CES Phase 0, Part 8)

## Purpose

This document records frontend-, design-system-, and background-processing-specific ambiguities surfaced while writing [85_Frontend_Architecture.md](85_Frontend_Architecture.md) through [93_Notification_Architecture.md](93_Notification_Architecture.md). It extends, and does not replace, the Open Questions documents from Parts 1–7. Ambiguity is recorded here rather than resolved by assumption.

## Scope

This document covers ambiguities in frontend and background-processing design left unresolved by documents 85–93. Numbering continues from [84_Open_Questions.md](84_Open_Questions.md) to maintain one unified backlog across all eight CES parts.

## Definitions

See [10_Glossary.md](10_Glossary.md). No new terms are introduced here.

## Open Questions

| # | Question | Why It Is Open | Related Document(s) | Blocks |
|---|---|---|---|---|
| 105 | What are the literal Design Token values — exact hex/color values for each semantic color, exact pixel values across the spacing/radius/shadow scales, exact motion durations and easing curves? | [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md) specifies token *categories* and named color choices (e.g., "Electric Blue") but not implementation values, consistent with this phase's specification-only scope. | 86 | Design System implementation, first component build. |
| 106 | What component library foundation does Cerebrum build on — fully custom components, or a headless primitive library (e.g., Radix, React Aria) providing accessibility/interaction behavior underneath the Design System's visual layer? | [87_Component_Library.md](87_Component_Library.md) catalogs components without committing to a build-from-scratch vs. headless-foundation approach, which has direct bearing on how quickly the nine-state contract (especially Accessibility) can be reliably met. | 87 | Component Library implementation start. |
| 107 | Is Knowledge Graph Cluster Mode computed client-side from already-retrieved graph data, or does it require a new backend Knowledge Graph Domain capability? | [90_Search_Experience.md](90_Search_Experience.md) explicitly flags this as unresolved. | 90 | Knowledge Graph Domain scope, Graph View implementation. |
| 108 | What rendering library and layout algorithm power the Graph View component for large-scale Knowledge Graphs? | [90_Search_Experience.md](90_Search_Experience.md) requires interactive, smooth-zooming, clustered graph rendering without specifying the technical approach, which has direct performance implications at the "millions of relationships" scale named in [41_Data_Architecture.md](41_Data_Architecture.md). | 90 | Graph View implementation, frontend performance budget. |
| 109 | What is the specific citation presentation format in the AI Chat UI — inline marker, footnote-style reference list, or hyperlinked text? | [57_Citation_Engine.md](57_Citation_Engine.md) (Part 5) and [89_AI_Chat_Architecture.md](89_AI_Chat_Architecture.md) (Part 8) both defer this presentation decision. | 89, 57 | AI Chat UI implementation. |
| 110 | What is the specific visual treatment distinguishing Retrieved Facts, AI Inferences, Recommendations, Assumptions, and Missing Information within a rendered AI Chat response? | [89_AI_Chat_Architecture.md](89_AI_Chat_Architecture.md) requires this distinction to be visually recoverable without specifying the treatment, and flags a need for user-comprehensibility validation once designed. | 89 | AI Chat UI implementation, user testing plan. |
| 111 | What is the data-model extension supporting Saved Searches (a named, persisted query+filter combination) — an extension of the Search Session entity, or a new entity category? | [90_Search_Experience.md](90_Search_Experience.md) defers this to architecture without resolving whether it fits within [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s existing 30-category taxonomy or requires an addition. | 90, 44 | Search Experience implementation, potential Entity Model extension. |
| 112 | Is Dashboard widget layout and arrangement fixed (platform-defined) or user-customizable in Version 1.0? | [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md) defers layout/arrangement and names user-customization only as a future consideration, without confirming V1.0's scope explicitly. | 88 | Dashboard implementation scope. |
| 113 | What is the Background Job entity's Archived-state retention period, and does it differ from content-entity retention given Jobs' primarily operational (not organizational-knowledge) value? | [92_Queue_Architecture.md](92_Queue_Architecture.md) flags this as likely warranting a shorter, Job-specific retention period without proposing one. | 92, 47 | Retention Sweep configuration for Background Job records. |
| 114 | What Job Priority levels exist, and what determines a Job's assigned priority (fixed per Task category, or dynamically assigned, e.g., user-triggered actions always outrank scheduled ones)? | [92_Queue_Architecture.md](92_Queue_Architecture.md) requires Priority as a Queue Feature without defining the priority scheme. | 92 | Background Processing Layer queue implementation. |
| 115 | What is the exhaustive, per-event-type Toast vs. Persistent notification classification, beyond the governing principle and illustrative examples given? | [93_Notification_Architecture.md](93_Notification_Architecture.md) states the governing rule but defers the complete mapping across every notifiable event type identified across Parts 2–8. | 93 | Notification Architecture implementation completeness. |
| 116 | What client-side performance monitoring tool captures the frontend-specific targets (Initial Load, Navigation, Dashboard) defined in [85_Frontend_Architecture.md](85_Frontend_Architecture.md), and how does it integrate with the backend's OpenTelemetry-based tracing ([38_Observability.md](38_Observability.md))? | The document requires these targets to be measured and monitored without specifying the tool or integration mechanism. | 85, 38 | Frontend Observability implementation. |

## Responsibilities

- No later-phase implementation may silently resolve one of these questions through an ad hoc code-level choice. Each must be closed via an ADR per [09_Governance.md](09_Governance.md), with this document updated to reflect the resolution.
- Question 106 (component library foundation) should be resolved early, given that it shapes how every subsequent component in [87_Component_Library.md](87_Component_Library.md) is built.

## Constraints

- This list reflects ambiguities identifiable from the Part 8 document set as currently written; it is not exhaustive of every future implementation-time decision.
- Not every "Deferred to Architecture" marker across documents 85–93 rises to the level of a tracked open question here — routine, low-risk implementation latitude is intentionally not tracked.

## Future Considerations

- As each question is resolved, move its row to a "Resolved Questions" section (to be added, mirroring the pattern in Parts 1–7's Open Questions documents) with a link to the governing ADR.
- With eight parts' worth of accumulated Open Questions (116 total across the full backlog), the consolidated cross-part index recommended since [74_Open_Questions.md](74_Open_Questions.md) is now strongly warranted before architecture-implementation work begins.

## Acceptance Criteria

- [ ] Every question is phrased so it can be answered with a concrete decision, not left as open-ended discussion.
- [ ] Every question cites the specific Part 8 document(s) it arose from.
- [ ] No question duplicates a question already recorded in any prior part's Open Questions document without adding frontend/background-processing-level specificity.
