# Port Allocation

All ports are host-mapped identically to each service's own default port,
for predictability. Every port is overridable via `.env` (see
`environment-variables.md`) if it conflicts with something else already
running on your machine.

| Port | Service | Purpose | Env Variable |
|---|---|---|---|
| 5432 | PostgreSQL | SQL protocol | `POSTGRES_PORT` |
| 7474 | Neo4j | Browser UI (HTTP) | `NEO4J_HTTP_PORT` |
| 7687 | Neo4j | Bolt protocol | `NEO4J_PORT` |
| 6379 | Redis | Redis protocol | `REDIS_PORT` |
| 6333 | Qdrant | HTTP / REST API | `QDRANT_PORT` |
| 6334 | Qdrant | gRPC API | `QDRANT_GRPC_PORT` |
| 9000 | MinIO | S3 API | `MINIO_API_PORT` |
| 9001 | MinIO | Web console | `MINIO_CONSOLE_PORT` |
| 9200 | OpenSearch | REST API | `OPENSEARCH_PORT` |
| 9600 | OpenSearch | Performance Analyzer | `OPENSEARCH_PERF_PORT` |

## Reserved for Future Use (Not Yet Provisioned)

| Port | Planned Service | Phase |
|---|---|---|
| 8000 | Backend (FastAPI) | Application phase, not this milestone |
| 3000 | Frontend (Next.js) | Application phase, not this milestone |
| 9090 | Prometheus | Phase 12 (Production Readiness), if self-hosted monitoring is added |
| 3001 | Grafana | Phase 12, same |

`BACKEND_PORT` and the frontend's dev-server port already appear in
`.env.example` for forward compatibility, but no service currently binds
them — see `infrastructure-overview.md`.

## Resolving a Port Conflict

If a port above is already in use on your machine, change the
corresponding variable in your local `.env` (never in
`docker-compose.yml` or `.env.example`) and re-run `scripts/start.sh`. See
`troubleshooting.md` for the specific symptom this produces.
