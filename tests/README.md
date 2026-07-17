# Cross-Cutting Tests

Full-stack tests that exercise both `apps/backend` and `apps/frontend`
together and don't belong to either one alone — most notably true
end-to-end browser tests (Playwright) driving the frontend against a live
backend and infrastructure stack.

This is distinct from `apps/backend/tests/` and `apps/frontend/tests/`,
which hold tests scoped to that single application. If a test only needs
one app running, it belongs there instead — keep it here only when it
genuinely spans both.

| Subdirectory | Scope |
|---|---|
| `unit/` | Reserved — cross-cutting unit-level concerns are rare; prefer app-scoped `tests/unit/` unless a genuine need arises. |
| `integration/` | Cross-service integration spanning multiple infrastructure components together. |
| `e2e/` | Full-stack, browser-driven end-to-end tests (Playwright) — the primary intended use of this directory. |
| `performance/` | Full-stack load/latency tests exercising frontend + backend + infrastructure together. |
| `ai-evaluation/` | Full-stack AI evaluation scenarios that need a live frontend, not only backend evaluation (see `apps/backend/tests/ai_evaluation/` for backend-only evaluation). |

No tests exist yet at this milestone.
