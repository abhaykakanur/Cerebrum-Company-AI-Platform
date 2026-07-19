# Cerebrum Frontend

The Thin Frontend Layer (Next.js/React/TypeScript). See
`docs/architecture/specification/85_Frontend_Architecture.md` for the full
architecture, including the binding Design-System-First mandate and the
"no business logic in UI" rule this package respects: every permission,
confidence, and citation decision is rendered as returned by the backend,
never recomputed client-side.

## Architecture Overview

Next.js App Router, organized as:

- `app/` — routes. `app/(app)/` is the authenticated shell (Dashboard,
  AI Chat, Search, Knowledge Graph, Documents, Connectors, Workflows,
  Employee Knowledge Capsules, Administration, Monitoring); `app/login`,
  `app/page.tsx`, and `app/workspaces/new` sit outside it since they
  render before a workspace/session exists.
- `components/ui/` — the Design System component catalog (doc 87), built
  by hand in the shadcn/ui pattern (Radix primitives + `class-variance-authority`,
  no CLI dependency).
- `layouts/` — the ten Layout System elements (doc 85): Top Nav, Sidebar,
  Command Palette, Workspace Switcher, Notification Center, Profile Menu,
  Context Drawer, Breadcrumbs, plus the Resizable Panels/Responsive Grid
  primitives in `components/ui/`.
- `lib/api/` — the typed HTTP client. `lib/api/client.ts` is the single
  chokepoint (auth headers, workspace scoping, envelope unwrapping,
  401-refresh-and-retry); one module per backend domain on top of it.
- `services/` — TanStack Query hooks wrapping `lib/api/` into
  feature-consumable data (request orchestration only, per the Thin
  Frontend principle — no business logic lives here either).
- `features/` — feature-specific components, composed exclusively from
  `components/ui/`.
- `providers/` — Query/Theme/Auth providers wired into `app/layout.tsx`.
- `utils/` — small, generic, dependency-free helpers (status→badge-variant
  mapping, design-token CSS-variable reads).

## Implemented Feature Areas

Dashboard, AI Chat (streaming via SSE, citations, confidence indicator,
conversation history/search/pin/export/regenerate), Enterprise Search
(hybrid/semantic/keyword/graph strategies, Ctrl+K command palette
integration), Knowledge Graph visualization (Cytoscape.js — explore/
cluster/dependency/timeline modes), Document Explorer (folders, upload,
versions, chunks, processing status), Connector Dashboard (registration,
health checks, sync history), Workflow Dashboard (visual step editor via
React Flow, execution history, templates, scheduling), Employee Knowledge
Capsule UI (expertise/ownership/collaboration, organizational timeline,
successor plan, bus-factor/coverage risk analysis), Administration
(organization/workspace settings), Monitoring (system health, connector
health, AI usage, index statistics).

Every feature area is scoped strictly to real, implemented backend
endpoints (`apps/backend/src/cerebrum/api/v1/`) — where a capability
described in the architecture docs has no corresponding backend endpoint
(user/role/audit-log administration, search-session persistence, message
feedback capture, an LLM-authored "AI Capsule narrative"), the UI either
omits it or implements an honestly-scoped, clearly-commented local-only
substitute rather than fabricating data. See the "Known Limitations"
section of the CIS Phase 5 Prompt 4 final implementation report for the
complete list.

## Public Interfaces

None — this is a leaf application, not a package other workspace members
import from. Other packages/apps never import from `apps/frontend`.

## Dependencies

- Node.js 20+, pnpm 9+
- Next.js 14 (App Router), React 18, TypeScript (strict mode), Tailwind CSS
- TanStack Query (data fetching/caching), Cytoscape.js (graph
  visualization), React Flow (workflow editor), Recharts (charts), cmdk
  (command palette), Radix UI primitives
- `@cerebrum/eslint-config`, `@cerebrum/tsconfig`, `@cerebrum/shared-types`
  (workspace packages)

## Configuration

`NEXT_PUBLIC_API_BASE_URL` — see `.env.example` at the repository root.
Inlined into the client bundle at **build time** (see
`docs/deployment/production-deployment.md`'s Building the Frontend Image
section) — changing the backend's public origin requires rebuilding the
image, not just restarting the container.

## Usage

```bash
# From the repository root:
pnpm install
pnpm --filter @cerebrum/frontend dev      # dev server at http://localhost:3000
pnpm --filter @cerebrum/frontend build    # production build
pnpm --filter @cerebrum/frontend test     # vitest unit tests
pnpm --filter @cerebrum/frontend lint     # eslint
pnpm --filter @cerebrum/frontend typecheck
```

A running backend (`apps/backend`) and its six datastores
(`infrastructure/docker/docker-compose.yml`) are required for any
authenticated page to load real data — every page beyond `/login` fetches
through `lib/api/`, never mock data.

## Known Limitations

- **No self-serve registration.** `cerebrum.api.v1.auth` has no signup
  route — accounts are provisioned out-of-band, so there is no Register
  page.
- **Pin/recent/saved searches are local-only** (`localStorage`), since no
  Search Session persistence endpoint exists in the backend yet.
- **Message feedback (thumbs up/down)** records nothing server-side —
  there is no feedback-capture endpoint; it's a session-local
  acknowledgement only.
- **No user/role/audit-log administration UI** — no corresponding backend
  endpoints exist.
- **No literal minimap** on the Knowledge Graph page — zoom/pan/fit
  controls exist, but a pixel-accurate viewport thumbnail was out of
  scope for this pass.
- **Cytoscape.js is not lazy-loaded**, making `/graph` the largest route
  bundle (~162 kB) — a real target for a future Performance Optimization
  pass, not yet addressed.
