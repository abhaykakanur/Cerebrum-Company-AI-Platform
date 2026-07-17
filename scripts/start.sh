#!/usr/bin/env bash
# Starts the entire Cerebrum local infrastructure (PostgreSQL, Neo4j, Redis,
# Qdrant, MinIO, OpenSearch) in the background.
#
# Usage: scripts/start.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::require_command docker
cerebrum::log "Starting infrastructure (postgres, neo4j, redis, qdrant, minio, opensearch)..."
cerebrum::compose up -d

cerebrum::log "Waiting for services to report healthy (this can take up to a minute on first run)..."
cerebrum::compose ps

cerebrum::log "Started. Run 'scripts/doctor.sh' to check health, or 'scripts/logs.sh' to follow logs."
