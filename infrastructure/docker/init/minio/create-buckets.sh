#!/bin/sh
# ==============================================================================
# Cerebrum — MinIO bucket initialization
#
# Runs once, via the one-shot `minio-init` service in docker-compose.yml,
# after MinIO reports healthy. Creates the application bucket if it does
# not already exist, then exits.
#
# Bucket naming and object-key convention:
# docs/architecture/specification/46_Multi_Tenancy.md — a single, shared
# bucket with tenant/workspace-prefixed object keys, not one bucket per
# tenant (avoiding per-account bucket-count ceilings at enterprise scale).
#
# This script creates the bucket only. It does not set lifecycle,
# versioning, or retention policy — see
# infrastructure/docker/configs/minio/README.md for why that is
# deliberately deferred.
# ==============================================================================

set -eu

MINIO_ALIAS="cerebrum-local"
BUCKET_NAME="${MINIO_BUCKET:-cerebrum-documents}"

echo "[minio-init] Configuring mc client alias..."
mc alias set "${MINIO_ALIAS}" http://minio:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

echo "[minio-init] Ensuring bucket '${BUCKET_NAME}' exists..."
if mc ls "${MINIO_ALIAS}/${BUCKET_NAME}" >/dev/null 2>&1; then
  echo "[minio-init] Bucket '${BUCKET_NAME}' already exists — nothing to do."
else
  mc mb "${MINIO_ALIAS}/${BUCKET_NAME}"
  echo "[minio-init] Bucket '${BUCKET_NAME}' created."
fi

echo "[minio-init] Done."
