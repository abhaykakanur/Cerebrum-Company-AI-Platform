# Docker Architecture

## Compose File Structure

`infrastructure/docker/docker-compose.yml` is intentionally a single file,
not split per-service — at six services, a single readable file is easier
to reason about than fragmented includes, consistent with
`docs/architecture/specification/04_Project_Principles.md`'s "Simple
architecture over unnecessary complexity." Splitting becomes worth
revisiting only once application services are added in a later phase.

## Named Volumes

Every service's persistent data lives in a named volume
(`cerebrum-<service>-data`), never a bind mount to the host filesystem
(except read-only configuration/init files). Named volumes are:

- **Portable** — identical behavior across macOS, Linux, and Windows/WSL2,
  where host-path bind mounts have historically had performance and
  permission inconsistencies.
- **Explicitly resettable** — `scripts/reset.sh` removes exactly these
  volumes and nothing else, giving a clean, complete reset with no
  leftover host-filesystem state.

## Health Checks

Every service defines a Docker-native `healthcheck:` block, used for two
things:

1. Docker's own container status (`docker ps`, `docker inspect`) reports
   `healthy`/`unhealthy`, which `scripts/doctor.sh` reads directly.
2. The `minio-init` one-shot job uses `depends_on: condition:
   service_healthy` to wait for MinIO before attempting bucket creation —
   the only inter-service dependency in this stack, since the six
   datastores are otherwise peers with no startup-order requirement
   between them.

## Restart Policy

Every long-running service uses `restart: unless-stopped` — it survives a
host reboot or Docker daemon restart without manual intervention, but
running `scripts/stop.sh` (or `docker compose down`) is respected and does
not fight the restart policy. The one-shot `minio-init` job explicitly
uses `restart: "no"`, since it is meant to run once and exit successfully,
not loop.

## Container and Network Naming

Every container is named `cerebrum-<service>` (e.g., `cerebrum-postgres`),
and the shared network is named `cerebrum-network` — both are fixed,
predictable names (via `container_name:` and the top-level `name:` under
`networks:`), not the auto-generated project-prefixed names Compose would
otherwise choose. This makes `docker ps`, `docker logs`, and manual
`docker exec` sessions unambiguous, and is what `scripts/doctor.sh` relies
on when it falls back to querying containers by name directly.

## Extending This Stack

Adding a new service (e.g., a future monitoring stack, per
`docs/architecture/specification/103_Engineering_Guidelines.md`'s
Observability quality, which remains a later-phase concern per this
milestone's explicit "no monitoring services yet" scope) follows the same
pattern every existing service already does:

1. Add the service block to `docker-compose.yml`, with a `container_name`,
   `healthcheck`, and named volume if it persists data.
2. Add its port(s) to `port-allocation.md`.
3. Add its configuration variables to `.env.example` and
   `environment-variables.md`.
4. Add it to `infrastructure/docker/healthchecks/check-all.sh`.

No other file needs to change — this is deliberately the entire extension
surface.
