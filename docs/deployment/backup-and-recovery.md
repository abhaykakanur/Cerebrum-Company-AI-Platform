# Backup and Recovery

How to back up and restore each of the six datastores provisioned by
[docker-architecture.md](docker-architecture.md). `scripts/backup.sh`
automates the PostgreSQL backup below; the other five are documented
here as manual commands rather than scripted, since each one's restore
procedure is a deliberate, reviewed action in a real incident — not
something a single script should perform unattended.

## Backup Priority

| Datastore  | Authoritative for                                                    | Rebuildable from another source?                                                                   |
| ---------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| PostgreSQL | Relational entities, RBAC, audit, conversations, workflows, capsules | No — the only true source of record                                                                |
| MinIO      | Original uploaded document bytes                                     | No — the only true source of record                                                                |
| Neo4j      | Entity/relationship graph                                            | Yes — re-derived by reprocessing documents already in MinIO through the extraction/entity pipeline |
| Qdrant     | Vector embeddings                                                    | Yes — re-derived by re-embedding chunks already in PostgreSQL                                      |
| OpenSearch | Keyword search index                                                 | Yes — re-derived by reindexing chunks already in PostgreSQL                                        |
| Redis      | Cache, sessions, rate limits                                         | Not meaningful to back up — purely ephemeral state                                                 |

PostgreSQL and MinIO are the two datastores that must actually be
backed up on a schedule; Neo4j/Qdrant/OpenSearch backups are an
optimization that saves reprocessing time during recovery, not a
correctness requirement.

## PostgreSQL

```bash
scripts/backup.sh                    # writes to ./backups/postgres-<timestamp>.sql.gz
```

Restore:

```bash
gunzip -c backups/postgres-<timestamp>.sql.gz | \
  docker exec -i cerebrum-postgres psql -U "${POSTGRES_USER:-cerebrum}" "${POSTGRES_DB:-cerebrum}"
```

## MinIO (document originals)

Mirror the bucket to a local directory or another S3-compatible target
using the MinIO client:

```bash
mc alias set cerebrum-local "http://localhost:${MINIO_API_PORT:-9000}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"
mc mirror cerebrum-local/"${MINIO_BUCKET:-cerebrum-documents}" ./backups/minio-$(date -u +%Y%m%dT%H%M%SZ)/
```

Restore is the same command with source and destination reversed.

## Neo4j

```bash
docker exec cerebrum-neo4j neo4j-admin database dump neo4j \
  --to-path=/data/backups
docker cp cerebrum-neo4j:/data/backups ./backups/neo4j-$(date -u +%Y%m%dT%H%M%SZ)
```

Restore (container must be stopped first — `neo4j-admin database load`
requires an offline database):

```bash
docker compose -f infrastructure/docker/docker-compose.yml stop neo4j
docker cp ./backups/neo4j-<timestamp>/neo4j.dump cerebrum-neo4j:/data/backups/neo4j.dump
docker exec cerebrum-neo4j neo4j-admin database load neo4j --from-path=/data/backups --overwrite-destination=true
docker compose -f infrastructure/docker/docker-compose.yml start neo4j
```

## Qdrant

Qdrant's snapshot API creates a point-in-time collection snapshot:

```bash
curl -X POST "http://localhost:${QDRANT_PORT:-6333}/collections/<collection_name>/snapshots"
```

The snapshot file is written inside the container's `/qdrant/storage`
volume; copy it out with `docker cp` the same way as the Neo4j dump
above. Restore via the equivalent `PUT
/collections/<collection_name>/snapshots/upload` API — see Qdrant's own
snapshot documentation for the exact restore payload, since it's
versioned independently of this repository.

## OpenSearch

```bash
# One-time: register a filesystem snapshot repository (already mounted
# via the opensearch service's volume in docker-compose.yml).
curl -X PUT "http://localhost:${OPENSEARCH_PORT:-9200}/_snapshot/cerebrum-backups" \
  -H 'Content-Type: application/json' \
  -d '{"type": "fs", "settings": {"location": "/usr/share/opensearch/backups"}}'

# Take a snapshot
curl -X PUT "http://localhost:${OPENSEARCH_PORT:-9200}/_snapshot/cerebrum-backups/snapshot-$(date -u +%Y%m%dT%H%M%SZ)?wait_for_completion=true"
```

Restore via `POST /_snapshot/cerebrum-backups/<snapshot_name>/_restore`.

## Redis

Not backed up — every value Redis holds (cache entries, rate-limit
counters, sessions) is either derivable from PostgreSQL or safe to lose
(a cold cache, reset rate-limit windows, forced re-login). If durability
is ever required for a future Redis-backed feature, revisit this
section rather than assuming it.

## Recommended Schedule

A daily PostgreSQL + MinIO backup, retained for at least 30 days, covers
the two datastores that cannot be reconstructed. Neo4j/Qdrant/OpenSearch
backups are worth taking weekly purely to shorten recovery time — full
reprocessing from PostgreSQL/MinIO is always the fallback if a backup is
missing or stale. This repository does not ship a cron/scheduler for
these commands — Deferred to Architecture, since the right mechanism
(host cron, a Kubernetes CronJob, a managed backup service) depends on
where this stack is actually deployed, which [production-deployment.md](production-deployment.md)
also leaves open.
