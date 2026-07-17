# 90 — Search Experience

## Purpose

This document defines the Search and Knowledge Graph frontend experiences, mapping each capability to the backend architecture already established in [70_Enterprise_Search.md](70_Enterprise_Search.md) through [72_Search_Ranking.md](72_Search_Ranking.md) (Part 6) and the Knowledge Graph Domain (Part 2/3). It covers both because they share a discovery-oriented interaction model and because no dedicated Knowledge Graph output document exists in this Part's deliverable list.

## Scope

This document covers the frontend presentation of search and graph exploration. It does not redefine search ranking, retrieval, or graph traversal mechanics — see Part 6 and [35_Domain_Architecture.md](35_Domain_Architecture.md)'s Knowledge Graph Domain.

## Definitions

See [10_Glossary.md](10_Glossary.md), [70_Enterprise_Search.md](70_Enterprise_Search.md). No new terms are introduced here.

## Search Experience

| Capability | Backend Mapping |
|---|---|
| Global search | [71_Search_Pipeline.md](71_Search_Pipeline.md)'s eleven-stage Search Pipeline. |
| Ctrl+K command palette | The Command Palette component ([87_Component_Library.md](87_Component_Library.md)), the primary entry point into Global search, consistent with [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s Layout System. |
| Instant suggestions | [71_Search_Pipeline.md](71_Search_Pipeline.md)'s Autocomplete, six suggestion types. |
| Hybrid search | FR-ES-003, the default search mode. |
| Graph search | [70_Enterprise_Search.md](70_Enterprise_Search.md)'s Graph Search type. |
| Semantic search | FR-ES-002. |
| Advanced filters | [71_Search_Pipeline.md](71_Search_Pipeline.md)'s thirteen Filtering dimensions, presented via Design System filter controls (Data Grid's built-in filtering per [87_Component_Library.md](87_Component_Library.md)). |
| Pinned searches | New UI-facing preference, backed by User Preference Memory ([59_Memory_Architecture.md](59_Memory_Architecture.md)), following the same pattern as AI Chat's Pin capability ([89_AI_Chat_Architecture.md](89_AI_Chat_Architecture.md)). |
| Recent searches | [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s Search Session entity, scoped to the requesting user. |
| Saved searches | A named, persisted filter/query combination — new UI-facing capability, backed by a Search Session extended with a saved flag and name (Deferred to Architecture for the specific data-model extension). |
| Highlighted snippets | [71_Search_Pipeline.md](71_Search_Pipeline.md)'s Relevant Snippet field, rendered with the matching terms visually emphasized. |

All search results rendered in this UI are already permission-filtered by the time they reach the frontend, per FR-ES-010 and the Thin Frontend principle ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)) — the frontend performs no client-side permission filtering of its own.

## Knowledge Graph Experience

| Capability | Backend Mapping |
|---|---|
| Interactive graph | FR-KG-008's Graph Visualization Data Support, rendered via the Graph View component ([87_Component_Library.md](87_Component_Library.md)). |
| Animated nodes | A Graph View rendering behavior using the Motion token ([86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)), bounded by the same <250ms-per-transition and Reduced Motion accessibility rules as every other Microinteraction ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)) — a large graph's initial layout animation is the one justified exception to strict 250ms bounding, since it is a one-time orientation aid rather than a per-interaction response, but SHALL still respect Reduced Motion by rendering statically when that preference is active. |
| Smooth zoom | Graph View interaction behavior, client-side rendering concern. |
| Cluster mode | A Graph View display mode grouping densely connected Knowledge Entities, aiding comprehension of large graphs — a presentation-layer grouping, not a new backend graph-clustering algorithm requirement (Deferred to Architecture on whether clustering is computed client-side from already-retrieved graph data or requested as a distinct backend capability). |
| Timeline mode | FR-KG-007's Entity and Relationship Timeline, rendered via the Timeline component ([87_Component_Library.md](87_Component_Library.md)). |
| Dependency mode | FR-KG-006/UC-10's dependency-finding traversal, rendered as a Graph View filtered to dependency-type relationships. |
| Mini-map | A Graph View navigation aid for large graphs, a presentation-layer feature with no backend data requirement beyond what Interactive graph already provides. |
| Relationship explorer | A Context Drawer ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)) presenting a selected entity's relationships in list form, complementing the visual Graph View with a scannable alternative. |
| Context panel | The Context Drawer applied specifically to a selected Knowledge Entity, surfacing its Citation-eligible source references ([57_Citation_Engine.md](57_Citation_Engine.md)) and Expertise Discovery-derived ownership (FR-ED-004). |

## Responsibilities

- Every Search and Knowledge Graph UI capability must be verified against its backend requirement's acceptance criteria, following the same discipline established in [89_AI_Chat_Architecture.md](89_AI_Chat_Architecture.md) for AI Chat.
- Cluster Mode's client-side-vs-backend-computed question must be resolved before implementation, given its direct bearing on whether this is purely a Frontend Layer concern or requires a new Knowledge Graph Domain capability.

## Constraints

- This document does not specify the Graph View's rendering library or layout algorithm — Deferred to Architecture.
- This document does not introduce new backend search or graph capabilities beyond what Part 2/3/6 already define — every capability listed maps to existing architecture.

## Future Considerations

- As Graph View is used with very large graphs (enterprise-scale Knowledge Graphs with potentially millions of entities per [41_Data_Architecture.md](41_Data_Architecture.md)'s stated scale), performance-driven design decisions (level-of-detail rendering, server-side pre-aggregation for Cluster Mode) should be revisited based on real usage patterns rather than assumed adequate from this specification alone.

## Acceptance Criteria

- [ ] All eleven Search Experience capabilities and all nine Knowledge Graph Experience capabilities from the governing specification are defined with backend mapping.
- [ ] Permission-filtering is confirmed as already applied before results reach the frontend, consistent with the Thin Frontend principle.
- [ ] Cluster Mode's open architectural question (client-side vs. backend-computed) is explicitly flagged rather than silently assumed.
