# 85 — Frontend Architecture

## Document Status

CES Version 1.0, Phase 0, Part 8. This document extends CES Phase 0 Parts 1–7 (documents 00–84) and does not rewrite them. It defines the Frontend Layer's complete architecture — philosophy, layout, responsiveness, accessibility, and performance — elaborating the Frontend Layer first placed in [30_System_Architecture.md](30_System_Architecture.md) and [31_Component_Architecture.md](31_Component_Architecture.md).

## Purpose

This document is the entry point into the Part 8 document set. It establishes the Frontend Philosophy, the binding rule that implementation begins with the Design System (not pages), the Layout System, and cross-cutting concerns (responsiveness, accessibility, microinteractions, performance) that apply across every subsequent Part 8 document.

## Scope

This document covers frontend-wide architecture and philosophy. It does not cover the Design System's visual language and tokens in detail (see [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)), the component catalog (see [87_Component_Library.md](87_Component_Library.md)), or specific feature UIs (Dashboard, AI Chat, Search — documents 88–90). No code, markup, or stylesheet content appears in this document or any Part 8 document, consistent with this specification's documentation-only scope.

## Definitions

- **Thin Frontend** — A frontend containing presentation logic only, with no business rules, no direct datastore access, and no AI reasoning/retrieval/permission-enforcement logic, per [30_System_Architecture.md](30_System_Architecture.md)'s Frontend Layer boundary.
- **Design System** — The single source of truth for every visual and interactive primitive the frontend uses, per Section 2's mandate below.

## Frontend Philosophy

Cerebrum's frontend SHALL evoke a premium, AI-native enterprise platform, characterized by: Premium, Modern, AI-first, Minimal, Elegant, Extremely fast, High information density, Zero visual clutter, Recruiter-impressive, Enterprise SaaS quality.

**Reference quality bar:** The UI SHALL evoke the quality of Linear, Vercel, Stripe Dashboard, Notion, Perplexity, Raycast, Arc Browser, and ChatGPT — as a quality and craft benchmark, not a visual template to copy. This distinction matters architecturally: the Design System ([86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)) defines Cerebrum's own coherent visual identity; these references establish the bar for polish, consistency, and restraint the Design System must meet, not a source to derive component shapes or color values from directly.

This philosophy is the frontend-specific expression of the "enterprise-grade SaaS platform serving thousands of organizations" ambition stated in [00_Project_Charter.md](00_Project_Charter.md) — a platform whose backend meets that bar but whose frontend looks like an internal tool would undermine the trust and adoption goals in [02_Project_Goals.md](02_Project_Goals.md).

## Design-System-First Mandate (Binding)

**Implementation SHALL NOT begin with pages.** Implementation SHALL begin by creating the Cerebrum Design System ([86_Enterprise_Design_System.md](86_Enterprise_Design_System.md), [87_Component_Library.md](87_Component_Library.md)). Every page MUST be built exclusively using reusable Design System components; no page may introduce custom visual styles outside the Design System.

This is the frontend-architecture equivalent of the Non-Negotiable Extraction Seam constraint in [30_System_Architecture.md](30_System_Architecture.md): just as backend domains may not reach into each other's infrastructure directly, no page may reach around the Design System to define its own visual treatment. The Design System becomes the single source of truth for every color, spacing, typography, and component decision — a page-level custom style is architecturally equivalent to a domain bypassing its repository port, and is a review-blocking finding under this mandate.

## Layout System

The application-wide layout SHALL be composed from the following ten elements, each a Design System component ([87_Component_Library.md](87_Component_Library.md)):

Top Navigation, Left Sidebar, Resizable Panels, Workspace Switcher, Command Palette, Notification Center, Profile Menu, Context Drawer, Breadcrumbs, Responsive Grid.

| Element | Backend Capability It Surfaces |
|---|---|
| Workspace Switcher | FR-OR-002 Multi-Workspace Organization Structure |
| Command Palette | [90_Search_Experience.md](90_Search_Experience.md)'s Ctrl+K global search |
| Notification Center | [93_Notification_Architecture.md](93_Notification_Architecture.md) |
| Profile Menu | User Management Domain ([35_Domain_Architecture.md](35_Domain_Architecture.md)) |
| Context Drawer | Contextual detail panels (e.g., a citation's source preview per FR-CT-002) |
| Breadcrumbs | Reflects [43_Canonical_Data_Model.md](43_Canonical_Data_Model.md)'s resource hierarchy (Organization → Workspace → resource) |

## Responsive Design

The Frontend SHALL support five device classes: Desktop, Laptop, Tablet, Mobile, Ultrawide. Every Design System component ([87_Component_Library.md](87_Component_Library.md)) SHALL define behavior across this range as one of its required states, consistent with that document's per-component requirements.

## Microinteractions

The Frontend SHALL provide smooth, purposeful feedback for: Hover, Click, Focus, Loading, Completion, Notifications — with transitions completing in under 250ms, consistent with the Frontend Philosophy's "Extremely fast" goal and distinct from, but complementary to, the backend Performance Targets below (a fast backend response delivered through a sluggish transition still reads as slow to the user).

## Accessibility

The Frontend SHALL meet WCAG AA, with: Keyboard navigation, Focus indicators, Reduced motion (honoring the user's OS-level reduced-motion preference, overriding the Microinteractions' default transitions), Screen reader support, Color contrast compliance. Accessibility is one of the nine required states every Design System component ([87_Component_Library.md](87_Component_Library.md)) supports, not a separate, optional audit pass — it is designed in from the Design-System-First mandate onward.

## Performance Targets

| Target | Value | Relationship to [39_Performance_Targets.md](39_Performance_Targets.md) |
|---|---|---|
| Initial Load | < 2 seconds | New — frontend-specific, not previously specified at the backend-architecture level. |
| Navigation | < 200 ms | New — client-side route transition, not a backend round-trip. |
| Search | < 2 seconds | Directly corresponds to the Search Response target. |
| Chat First Token | < 3 seconds | Directly corresponds to the Chat Response First Token target. |
| Dashboard | < 2 seconds | New — aggregate load time for [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)'s widget set. |

These targets are measured client-side (time to interactive/rendered), inclusive of but not identical to the backend targets they correspond to — a backend meeting its 2-second Search Response target does not guarantee the frontend's 2-second Search target if rendering or network transfer adds material overhead; both must be individually met.

## Thin Frontend: No Business Logic in UI

Restating and binding [30_System_Architecture.md](30_System_Architecture.md)'s Frontend Layer boundary for this Part's validation checklist: the frontend contains presentation logic only. It never accesses a datastore directly. It never performs AI reasoning, retrieval ranking, or permission-enforcement decisions — those are server-side only, consumed via the API Domain ([80_API_Architecture.md](80_API_Architecture.md)). A frontend component that, for instance, locally filters search results by permission (rather than trusting the server's already-filtered response) would violate this boundary and duplicate — with likely divergence risk — logic that must remain single-sourced in the Authorization Layer.

## Responsibilities

- Every new page or feature introduced in a later phase must be built exclusively from Design System components, verified in review before merge.
- Performance targets in this document must be measured and monitored via the same Observability architecture ([38_Observability.md](38_Observability.md)) already established for backend targets, extended with frontend-specific instrumentation (Deferred to Architecture for the specific client-side monitoring tool).

## Constraints

- This document does not specify a frontend framework beyond what [32_Technology_Stack.md](32_Technology_Stack.md) already established (Next.js, React, TypeScript).
- This document does not contain visual design values (colors, exact spacing) — see [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md).

## Future Considerations

- As Ultrawide and Mobile usage patterns are observed post-launch, the relative design priority across the five device classes may warrant revisiting — the initial assumption (Desktop/Laptop primary, given Cerebrum's enterprise-knowledge-worker context) should be validated against real usage data.

## Acceptance Criteria

- [ ] The Frontend Philosophy's ten design goals and reference quality bar are stated, with the reference bar explicitly scoped as a craft benchmark, not a template to copy.
- [ ] The Design-System-First mandate is stated as binding, with its architectural parallel to the Extraction Seam constraint made explicit.
- [ ] All ten Layout System elements are defined with their backend capability linkage.
- [ ] Responsive Design's five device classes, Microinteractions' six categories and <250ms rule, Accessibility's five WCAG AA elements, and all five Performance Targets are addressed.
- [ ] The Thin Frontend / no-business-logic-in-UI rule is restated as binding with a concrete violation example.
