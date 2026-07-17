#!/usr/bin/env bash
# Follows logs for the Cerebrum local infrastructure.
#
# Usage:
#   scripts/logs.sh                 # all services
#   scripts/logs.sh postgres        # a single service
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::require_command docker

if [ "$#" -eq 0 ]; then
  cerebrum::log "Following logs for all services (Ctrl+C to stop)..."
  cerebrum::compose logs -f --tail=200
else
  cerebrum::log "Following logs for '$1' (Ctrl+C to stop)..."
  cerebrum::compose logs -f --tail=200 "$1"
fi
