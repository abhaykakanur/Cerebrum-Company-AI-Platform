# Import Rules

The mechanical, file-level counterpart to `docs/architecture/dependency-rules.md`
(which governs *which layer may depend on which*). This document governs
*how imports are written* once a dependency is legitimate.

## Python

- **Absolute imports only** from the `cerebrum` package root — never
  relative imports (`from .. import x`) crossing a layer boundary. A
  relative import *within* the same subpackage (e.g., within
  `domain/identity/`) is fine once that subpackage exists.
- **Import ordering** is enforced by isort (`profile = "black"`, see root
  `pyproject.toml`): standard library, then third-party, then
  `cerebrum`-internal, each group alphabetized, separated by a blank line.
  Run `scripts/format.sh` rather than ordering by hand.
- **No wildcard imports** (`from module import *`) anywhere.
- **No import-time side effects** — importing a module must never open a
  database connection, make a network call, or mutate global state.
  Initialization happens explicitly, in `core/`'s composition root, not as
  a side effect of `import cerebrum.infrastructure.postgres`.

## TypeScript

- **Path aliases** (`@/*` in `apps/frontend/tsconfig.json`) are used for
  intra-app imports; workspace packages are imported by their package
  name (`@cerebrum/shared-types`), never by relative path reaching across
  the monorepo (`../../../packages/shared-types/src`).
- **Import ordering** is enforced by ESLint/Prettier, not hand-sorted.
- **No default exports** for anything except Next.js's required
  conventions (`page.tsx`, `layout.tsx`) — named exports make refactoring
  and auto-import tooling more reliable, and are required for tree-shaking
  clarity in shared packages.
- **Type-only imports** use `import type { ... }` — never mix runtime and
  type imports in a way that obscures which is which.

## Both Languages

- An import that only exists to satisfy `docs/architecture/dependency-rules.md`'s
  layering (i.e., you had to restructure code to make the import legal)
  is a signal the restructuring was correct, not a workaround to route
  around — never "fix" a layering violation by adding a local re-export
  that quietly bypasses the rule.
