#!/usr/bin/env bash
# Stops the Cerebrum local infrastructure without removing data volumes.
#
# Usage: scripts/stop.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::require_command docker
cerebrum::log "Stopping infrastructure (data volumes are preserved — use scripts/reset.sh to discard them)..."
cerebrum::compose down

cerebrum::log "Stopped."
