# 87 — Component Library

## Purpose

This document catalogs the thirty-three reusable components comprising the Cerebrum Design System's component layer, organized by functional category, and defines the nine states every component SHALL support. It is the concrete inventory the Design-System-First mandate ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)) requires every page to build from exclusively.

## Scope

This document covers component inventory, categorization, and required states. It does not specify component implementation (markup, styling, framework code) — Deferred to Architecture, consistent with this specification's documentation-only scope. It does not repeat token definitions — see [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md).

## Definitions

- **Component State** — A distinct visual/interactive mode a component must support, verified independently of its other states.

## Universal Component State Contract

Every component in this catalog SHALL support the following nine states:

Hover, Focus, Disabled, Loading, Error, Success, Dark, Light, Accessibility.

This is a binding contract, not a per-component checklist to selectively apply — a component shipped without, for instance, a defined Loading state is incomplete per the Design-System-First mandate, even if that state seems inapplicable at first glance (e.g., a Tooltip's "Loading" state may simply be "not rendered until content is ready," but that decision must be deliberate and documented, not merely absent). "Accessibility" as a state specifically means the component's keyboard-navigable, screen-reader-compatible, and focus-indicator behavior per [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s WCAG AA requirement — verified per-component, not only at the page level.

## Component Catalog

### Form & Input
Buttons, Inputs, Search Bars, Dropdowns, Selects, Checkboxes, Radio Buttons

These components form the primary means of user input and action-triggering across the platform. Search Bars specifically integrate with [90_Search_Experience.md](90_Search_Experience.md)'s Query Rewriting-aware suggestion behavior; Buttons carry an explicit destructive/danger variant (using the `color-danger` token from [86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)) for irreversible actions, consistent with this specification's broader emphasis on deliberate handling of destructive operations.

### Navigation
Tabs, Breadcrumbs, Pagination, Command Palette

Breadcrumbs render the resource hierarchy per [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s Layout System. Pagination supports both Offset and Cursor pagination display modes, reflecting [81_API_Standards.md](81_API_Standards.md)'s two supported pagination types transparently to the underlying API contract in use. Command Palette is the Ctrl+K global entry point detailed in [90_Search_Experience.md](90_Search_Experience.md).

### Overlay & Layering
Dialogs, Drawers, Context Menu, Tooltips

These components use the Elevation and Z-index tokens ([86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)) exclusively for stacking order — no overlay component defines an ad hoc z-index. Drawers specifically realize the Layout System's Context Drawer element.

### Data Display
Cards, Glass Cards, Tables, Data Grid, Avatars, Badges, Tags, Tree View

Glass Cards apply the Premium Glassmorphism visual language ([86_Enterprise_Design_System.md](86_Enterprise_Design_System.md)) as a distinct variant from standard Cards, used for elevated, focal content (e.g., a Dashboard KPI, per [88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)). Data Grid is the higher-density, sortable/filterable variant of Table, supporting [81_API_Standards.md](81_API_Standards.md)'s Filtering dimensions directly in its UI controls. Tree View renders hierarchical data (e.g., folder structures per FR-DM-005, or the RBAC role hierarchy per [78_RBAC_Model.md](78_RBAC_Model.md)).

### Feedback & Status
Toast, Notification Center, Progress Indicators, Skeleton Loader, Timeline, Accordion

Toast provides transient, non-blocking feedback; Notification Center provides persistent, reviewable notification history — the two are visually and behaviorally distinct components serving [93_Notification_Architecture.md](93_Notification_Architecture.md)'s different notification categories. Skeleton Loader is the Design System's standard loading-state placeholder, used wherever content is being fetched, directly supporting the Frontend Philosophy's "Extremely fast"-*feeling* goal even when actual data fetch takes longer than instantaneous. Timeline renders chronologically ordered content (per FR-KG-007, [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md)'s Timeline View output format, and [70_Enterprise_Search.md](70_Enterprise_Search.md)'s Timeline Search).

### Content Rendering
Charts, Graph View, Markdown Viewer, Code Viewer

Charts render Dashboard and Analytics data ([88_Dashboard_Architecture.md](88_Dashboard_Architecture.md)). Graph View is the Knowledge Graph visualization component, detailed in [90_Search_Experience.md](90_Search_Experience.md), consuming FR-KG-008's Graph Visualization Data Support output. Markdown Viewer and Code Viewer render AI Chat responses ([89_AI_Chat_Architecture.md](89_AI_Chat_Architecture.md))'s Markdown and Code Block output formats per [56_Reasoning_Architecture.md](56_Reasoning_Architecture.md).

## Responsibilities

- Every new UI need identified in a later phase must first be checked against this catalog before a new component is proposed — component proliferation (near-duplicate components with marginal differences) should be resisted in favor of extending an existing component's variants, mirroring the same discipline [78_RBAC_Model.md](78_RBAC_Model.md) applies to resisting role sprawl.
- Every component addition must define all nine required states before being considered complete and available for page use.

## Constraints

- This document does not specify component APIs (props, slots, composition patterns) — Deferred to Architecture.
- This document does not mandate a specific component library foundation (built fully custom vs. built atop a headless component primitive library) — Deferred to Architecture.

## Future Considerations

- As usage patterns emerge, this catalog should be reviewed for components that prove rarely used (candidates for consolidation) or for gaps where pages have resorted to one-off styling despite the Design-System-First mandate (a signal the catalog needs a genuine addition, not that the mandate should be relaxed).

## Acceptance Criteria

- [ ] All thirty-three components from the governing specification are catalogued, organized by functional category.
- [ ] The nine-state Universal Component State Contract is defined as binding for every component, not merely a suggested checklist.
- [ ] Each category's components are connected to the specific backend capability or other Part 8 document they serve, avoiding a purely decorative listing.
