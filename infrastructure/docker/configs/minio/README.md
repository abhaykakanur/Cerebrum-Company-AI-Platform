# MinIO Configuration

At this milestone, MinIO is configured through environment variables
(root credentials) in `docker-compose.yml`. Bucket creation is handled by
the one-shot `minio-init` service — see
`infrastructure/docker/init/minio/create-buckets.sh`.

The bucket naming convention follows
`docs/architecture/specification/46_Multi_Tenancy.md`'s prefix-based
tenant isolation: a single bucket (`MINIO_BUCKET`, default
`cerebrum-documents`) with tenant/workspace-prefixed object keys
(`{tenant_id}/{workspace_id}/{entity_type}/{entity_id}/{filename}`), rather
than one bucket per tenant.

**This directory is reserved** for future bucket lifecycle policy
templates (retention, versioning) once
`docs/architecture/specification/47_Data_Governance.md`'s Retention Sweep
is implemented.
