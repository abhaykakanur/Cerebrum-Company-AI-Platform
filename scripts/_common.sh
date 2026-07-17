#!/usr/bin/env bash
# ==============================================================================
# Cerebrum — shared shell helpers, sourced by every script in this directory.
# Not intended to be run directly.
# ==============================================================================

set -euo pipefail

# Resolve the repository root regardless of the caller's current directory.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/infrastructure/docker/docker-compose.yml"
ENV_FILE="${REPO_ROOT}/.env"

cerebrum::require_env_file() {
  if [ ! -f "${ENV_FILE}" ]; then
    echo "No .env file found at repository root."
    echo "Creating one from .env.example — review and adjust values before continuing."
    cp "${REPO_ROOT}/.env.example" "${ENV_FILE}"
  fi
}

cerebrum::compose() {
  cerebrum::require_env_file
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"
}

cerebrum::log() {
  printf "\033[1;34m[cerebrum]\033[0m %s\n" "$1"
}

cerebrum::require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command '$1' was not found on PATH. See docs/development/getting-started.md."
    exit 1
  fi
}
