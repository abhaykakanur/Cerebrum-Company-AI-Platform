# Cerebrum Frontend

The Thin Frontend Layer (Next.js/React/TypeScript). See
`docs/architecture/specification/85_Frontend_Architecture.md` for the full
architecture, including the binding Design-System-First mandate and the
"no business logic in UI" rule this package must respect.

## Architecture Overview

Standard Next.js App Router structure, extended with the feature/component
organization described in `docs/architecture/specification/87_Component_Library.md`.
See each subdirectory's own `README.md` for its specific responsibility.

## Public Interfaces

None — this package consumes the backend's API exclusively through
`lib/`'s API client (not yet implemented, since no backend API endpoints
exist yet).

## Dependencies

- Node.js 20+, pnpm 9+
- Next.js, React, TypeScript (strict mode), Tailwind CSS
- `@cerebrum/eslint-config`, `@cerebrum/tsconfig`, `@cerebrum/shared-types` (workspace packages)

## Configuration

`NEXT_PUBLIC_API_BASE_URL` — see `.env.example` at the repository root.

## Usage

```bash
# From the repository root:
pnpm install
pnpm --filter @cerebrum/frontend dev
```

Serves a placeholder page at <http://localhost:3000> proving the build
pipeline works — no application UI exists yet.

## Limitations

- No pages beyond the placeholder root route.
- No authentication, no data fetching, no business components.
- Design Tokens (`tailwind.config.ts`) are structurally present but
  unpopulated — see
  `docs/architecture/specification/86_Enterprise_Design_System.md`.
