#!/usr/bin/env bash
# Formats all Python and TypeScript code in place (Black + isort, Prettier).
#
# Usage: scripts/format.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::log "Formatting Python (black, isort)..."
(cd "${REPO_ROOT}" && uv run black apps/backend && uv run isort apps/backend)

cerebrum::log "Formatting TypeScript/JS/JSON/Markdown (prettier)..."
(cd "${REPO_ROOT}" && pnpm run format)

cerebrum::log "Format complete."
