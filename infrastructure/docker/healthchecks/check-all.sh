#!/usr/bin/env bash
# ==============================================================================
# Cerebrum — Aggregate infrastructure health check
#
# Distinct from the per-container `healthcheck:` blocks in docker-compose.yml
# (which Docker uses internally to gate `depends_on: condition: service_healthy`
# and to mark a container's own status). This script is the host-side,
# human-facing check invoked by `scripts/doctor.sh` — it reports pass/fail
# for every service in one place, from outside the containers, the way a
# developer or CI job actually wants to consume health status.
#
# Exit code: 0 if every service is healthy, 1 if any service is not.
# ==============================================================================

set -uo pipefail

COMPOSE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docker-compose.yml"
FAILURES=0

check() {
  local name="$1"
  local description="$2"
  shift 2
  if "$@" >/dev/null 2>&1; then
    printf "  \033[32m✓\033[0m %-12s %s\n" "$name" "$description"
  else
    printf "  \033[31m✗\033[0m %-12s %s\n" "$name" "$description"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "Cerebrum Infrastructure Health Check"
echo "====================================="

# Prefer Docker's own healthcheck status (matches docker-compose.yml exactly)
# where the Docker CLI is available; fall back to a direct port probe otherwise.
if command -v docker >/dev/null 2>&1; then
  for svc in postgres neo4j redis qdrant minio opensearch; do
    container="cerebrum-${svc}"
    status="$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not-running")"
    if [ "$status" = "healthy" ]; then
      printf "  \033[32m✓\033[0m %-12s healthy\n" "$svc"
    else
      printf "  \033[31m✗\033[0m %-12s %s\n" "$svc" "$status"
      FAILURES=$((FAILURES + 1))
    fi
  done
else
  echo "  (docker CLI not found — falling back to direct port probes)"
  check postgres   "port 5432 reachable"   bash -c "echo > /dev/tcp/localhost/${POSTGRES_PORT:-5432}"
  check neo4j       "HTTP 7474 reachable"   curl -sf "http://localhost:${NEO4J_HTTP_PORT:-7474}"
  check redis        "port 6379 reachable"   bash -c "echo > /dev/tcp/localhost/${REDIS_PORT:-6379}"
  check qdrant        "port 6333 reachable"   curl -sf "http://localhost:${QDRANT_PORT:-6333}/healthz"
  check minio           "health endpoint OK"   curl -sf "http://localhost:${MINIO_API_PORT:-9000}/minio/health/live"
  check opensearch       "cluster health OK"    curl -sf "http://localhost:${OPENSEARCH_PORT:-9200}/_cluster/health"
fi

echo "====================================="
if [ "$FAILURES" -eq 0 ]; then
  echo "All services healthy."
  exit 0
else
  echo "${FAILURES} service(s) unhealthy. Run 'scripts/logs.sh <service>' to investigate."
  echo "See docs/deployment/troubleshooting.md for common causes."
  exit 1
fi
