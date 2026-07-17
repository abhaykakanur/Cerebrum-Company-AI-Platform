#!/usr/bin/env bash
# Runs the backend and frontend test suites.
#
# Usage:
#   scripts/test.sh              # unit tests only (fast, default)
#   scripts/test.sh --all        # unit + integration + e2e (requires
#                                 # infrastructure running — see scripts/start.sh)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

MARKER="unit"
if [ "${1:-}" = "--all" ]; then
  MARKER=""
fi

cerebrum::log "Running backend tests (pytest)..."
if [ -n "${MARKER}" ]; then
  (cd "${REPO_ROOT}" && uv run pytest -m "${MARKER}")
else
  (cd "${REPO_ROOT}" && uv run pytest)
fi

cerebrum::log "Running frontend tests..."
(cd "${REPO_ROOT}" && pnpm run test)

cerebrum::log "Tests complete."
