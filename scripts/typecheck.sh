#!/usr/bin/env bash
# Type-checks all Python (mypy --strict) and TypeScript (tsc --strict) code.
#
# Usage: scripts/typecheck.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::log "Type-checking Python (mypy)..."
(cd "${REPO_ROOT}" && uv run mypy apps/backend/src)

cerebrum::log "Type-checking TypeScript (tsc)..."
(cd "${REPO_ROOT}" && pnpm run typecheck)

cerebrum::log "Type check complete."
