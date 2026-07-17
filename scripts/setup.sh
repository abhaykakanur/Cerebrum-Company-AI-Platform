#!/usr/bin/env bash
# One-time (or repeatable) environment setup: installs dependencies for both
# workspaces, provisions a local .env, starts infrastructure, and waits for
# it to become healthy.
#
# Usage: scripts/setup.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::require_command node
cerebrum::require_command pnpm
cerebrum::require_command uv
cerebrum::require_command docker

cerebrum::require_env_file

cerebrum::log "Installing frontend/package dependencies (pnpm)..."
(cd "${REPO_ROOT}" && pnpm install)

cerebrum::log "Installing backend dependencies (uv)..."
(cd "${REPO_ROOT}" && uv sync)

cerebrum::log "Installing pre-commit hooks..."
if command -v pre-commit >/dev/null 2>&1; then
  (cd "${REPO_ROOT}" && pre-commit install)
else
  echo "  pre-commit not found on PATH — install it (e.g. 'uv tool install pre-commit') and re-run 'pre-commit install'."
fi

cerebrum::log "Starting local infrastructure..."
"${REPO_ROOT}/scripts/start.sh"

cerebrum::log "Setup complete. Run 'scripts/doctor.sh' to verify everything is healthy."
