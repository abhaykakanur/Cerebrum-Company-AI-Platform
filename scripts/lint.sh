#!/usr/bin/env bash
# Lints all Python and TypeScript code. Exits non-zero on any warning —
# per docs/architecture/specification/99_Coding_Standards.md, no lint
# warnings are allowed to merge.
#
# Usage: scripts/lint.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::log "Linting Python (ruff)..."
(cd "${REPO_ROOT}" && uv run ruff check apps/backend)

cerebrum::log "Linting TypeScript/JS (eslint)..."
(cd "${REPO_ROOT}" && pnpm run lint)

cerebrum::log "Lint complete — no warnings."
