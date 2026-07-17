#!/usr/bin/env bash
# Stops the Cerebrum local infrastructure and PERMANENTLY DELETES all data
# volumes (Postgres data, Neo4j graph, Redis cache, Qdrant vectors, MinIO
# objects, OpenSearch indexes). Use this to return to a completely clean
# infrastructure state.
#
# Usage: scripts/reset.sh [--yes]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::require_command docker

if [ "${1:-}" != "--yes" ]; then
  echo "This will permanently delete ALL local infrastructure data volumes:"
  cerebrum::compose config --volumes 2>/dev/null | sed 's/^/  - /' || true
  read -r -p "Type 'reset' to confirm: " confirmation
  if [ "${confirmation}" != "reset" ]; then
    echo "Aborted. No changes made."
    exit 1
  fi
fi

cerebrum::log "Removing containers and volumes..."
cerebrum::compose down --volumes --remove-orphans

cerebrum::log "Infrastructure reset. Run 'scripts/start.sh' to provision a fresh environment."
