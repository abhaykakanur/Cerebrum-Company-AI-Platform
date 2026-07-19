#!/usr/bin/env bash
# Backs up PostgreSQL — the authoritative relational datastore
# (docs/architecture/specification/42_Database_Responsibilities.md) and
# the only one of the six datastores with no rebuild-from-source path
# (Neo4j/Qdrant/OpenSearch content is re-derivable by reprocessing
# documents already in MinIO/Postgres; MinIO's own objects are the
# original uploads themselves). See docs/deployment/backup-and-recovery.md
# for backing up the other five datastores and for restore procedures —
# this script deliberately does one thing, matching every other script
# in this directory.
#
# Usage: scripts/backup.sh [output-directory]  (defaults to ./backups)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::require_command docker
cerebrum::require_env_file

OUTPUT_DIR="${1:-${REPO_ROOT}/backups}"
mkdir -p "${OUTPUT_DIR}"

# shellcheck disable=SC1090
set -a; source "${ENV_FILE}"; set +a

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="${OUTPUT_DIR}/postgres-${TIMESTAMP}.sql.gz"

cerebrum::log "Backing up PostgreSQL (${POSTGRES_DB:-cerebrum}) to ${OUTPUT_FILE}..."
docker exec cerebrum-postgres pg_dump \
  --username "${POSTGRES_USER:-cerebrum}" \
  --no-owner \
  --format=plain \
  "${POSTGRES_DB:-cerebrum}" | gzip > "${OUTPUT_FILE}"

cerebrum::log "Done. Restore with: gunzip -c ${OUTPUT_FILE} | docker exec -i cerebrum-postgres psql -U ${POSTGRES_USER:-cerebrum} ${POSTGRES_DB:-cerebrum}"
