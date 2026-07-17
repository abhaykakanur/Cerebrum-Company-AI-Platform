# Naming Conventions

## Python (`apps/backend/`)

| Element | Convention | Example |
|---|---|---|
| Modules, packages, files | `snake_case` | `user_repository.py` |
| Classes | `PascalCase` | `class WorkspaceRepository` |
| Interfaces (Protocols) | `PascalCase`, named for capability, no `I`-prefix | `class SupportsHealthCheck(Protocol)` |
| Functions, variables | `snake_case` | `def create_workspace()` |
| Constants | `UPPER_CASE` | `DEFAULT_PAGE_SIZE = 50` |
| Private members | leading underscore | `_internal_cache` |

## TypeScript (`apps/frontend/`, `packages/`)

| Element | Convention | Example |
|---|---|---|
| Components | `PascalCase` | `SearchBar.tsx` |
| Variables, functions | `camelCase` | `const activeWorkspace = ...` |
| Types, interfaces | `PascalCase`, no `I`-prefix | `interface SearchResult` |
| Constants | `UPPER_CASE` for true constants, `camelCase` for config objects | `MAX_RETRIES`, `defaultQueryOptions` |
| Routes/URL paths | `kebab-case` | `/knowledge-graph` |
| Files (non-component) | `kebab-case` | `api-client.ts` |

## File and Directory Naming

- Directory names match the domain/concept they represent, `snake_case`
  (Python) or `kebab-case` (TypeScript) — never abbreviated beyond common,
  unambiguous industry abbreviations (`api`, `db`, `config`).
- Test files mirror the file they test: `workspace_service.py` →
  `test_workspace_service.py`; `SearchBar.tsx` → `SearchBar.test.tsx`.

## Requirement Traceability in Names

Where a class, function, or module implements a specific CES functional
requirement, prefer naming that makes the connection findable (e.g., a
docstring or comment citing `FR-WS-003`) over embedding the requirement ID
in the identifier itself — identifiers should read naturally in code;
traceability lives in `docs/architecture/specification/106_Requirement_Traceability.md`
and comments, not in verbose names.

## Cross-Reference

For the deeper *why* behind strong typing and explicit naming, see
`docs/architecture/specification/99_Coding_Standards.md`.
