#!/usr/bin/env bash
# Removes build artifacts, caches, and dependency directories from both
# workspaces. Does NOT touch infrastructure data volumes — use
# scripts/reset.sh for that.
#
# Usage: scripts/clean.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::log "Removing Python build artifacts and caches..."
find "${REPO_ROOT}/apps/backend" -type d \( -name "__pycache__" -o -name "*.egg-info" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" \) -prune -exec rm -rf {} +
rm -rf "${REPO_ROOT}/apps/backend/dist" "${REPO_ROOT}/apps/backend/build"

cerebrum::log "Removing Node/TypeScript build artifacts and caches..."
find "${REPO_ROOT}" -type d -name "node_modules" -prune -exec rm -rf {} +
find "${REPO_ROOT}" -type d -name ".next" -prune -exec rm -rf {} +
find "${REPO_ROOT}" -type d -name ".turbo" -prune -exec rm -rf {} +

cerebrum::log "Clean complete. Run 'scripts/setup.sh' to reinstall dependencies."
