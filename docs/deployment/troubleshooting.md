# Troubleshooting Guide

## A Service Won't Start / Stays Unhealthy

1. Check its logs: `scripts/logs.sh <service>`.
2. Check `scripts/doctor.sh` output for which specific service is failing.
3. Common causes:
   - **Port already in use** — another process on your machine is already
     bound to one of the ports in `port-allocation.md`. Symptom: the
     container exits immediately, or `docker compose up` errors with
     "port is already allocated." Fix: change the corresponding
     `*_PORT` variable in your local `.env`, then `scripts/stop.sh &&
     scripts/start.sh`.
   - **Stale volume from an incompatible previous version** — symptom:
     a service crash-loops with a data-format or migration error in its
     logs immediately after you pulled a Docker image update. Fix:
     `scripts/reset.sh` (destroys local data — safe in development).
   - **Insufficient memory allocated to Docker** — OpenSearch and Neo4j
     both need real memory headroom (each is configured for roughly
     512MB–1GB heap). On Docker Desktop, check Settings → Resources and
     ensure at least 4GB is allocated to Docker overall.

## `scripts/*.sh: Permission denied`

The scripts should already be executable in a fresh clone (Git preserves
the executable bit). If not:

```bash
chmod +x scripts/*.sh
```

## `.env` Not Found / Variables Not Substituted

`scripts/start.sh` (via `scripts/_common.sh`) automatically creates `.env`
from `.env.example` if missing. If you're invoking `docker compose`
directly instead of through the scripts, make sure to pass
`--env-file .env` explicitly and run the command from the repository
root — see `docs/deployment/docker-architecture.md`.

## MinIO Bucket Wasn't Created

Check the one-shot init job's logs — it runs once and exits, so it won't
appear in `docker compose ps` as a running service:

```bash
docker compose -f infrastructure/docker/docker-compose.yml logs minio-init
```

If it failed, re-run it directly:

```bash
docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up minio-init
```

## OpenSearch: "max virtual memory areas vm.max_map_count is too low"

This is a host kernel setting OpenSearch requires, common on Linux hosts
(rare on Docker Desktop for macOS/Windows, which configures this
automatically inside its VM). If you see this error in
`scripts/logs.sh opensearch`, run on the Docker **host** (not inside a
container):

```bash
sudo sysctl -w vm.max_map_count=262144
```

This does not persist across a host reboot; see the OpenSearch
documentation for a permanent fix if you hit this repeatedly.

## "This configuration is for local development only" — What Needs to Change for Staging/Production?

Several settings in `docker-compose.yml` are explicitly local-development
shortcuts, each commented in place:

- **OpenSearch security plugin is disabled** (`DISABLE_SECURITY_PLUGIN:
  "true"`). Production MUST enable it with proper TLS and role-based
  access — this is explicitly out of scope for this milestone and tracked
  in `docs/architecture/specification/49_Open_Questions.md`, Open
  Question 55.
- **Redis, PostgreSQL, Neo4j, and MinIO credentials** are simple
  placeholder values suitable only for a network-isolated local
  container. Production credentials are retrieved via the Security
  Domain's `GetSecret` port, never placed in an environment file — see
  `docs/architecture/specification/75_Security_Architecture.md`.
- **No TLS** on any service's internal connections — acceptable on a
  local Docker bridge network, not acceptable in any shared or networked
  environment.

Do not deploy this compose file, unmodified, anywhere other than a
developer's own machine.

## I Changed `docker-compose.yml` and Now Nothing Starts

Validate the file's YAML syntax and Compose semantics before debugging
further:

```bash
docker compose -f infrastructure/docker/docker-compose.yml config
```

This prints the fully resolved configuration (with variables substituted)
or a precise syntax/semantic error if something is wrong — much faster to
read than a failed `up`.

## The Backend Won't Start: `ConfigurationException: ... is still set to its local-development placeholder value`

As of CIS Phase 1 Prompt 7, `Settings` refuses to start in a
`staging`/`production` `ENVIRONMENT` if `POSTGRES_PASSWORD`,
`REDIS_PASSWORD`, `NEO4J_PASSWORD`, `MINIO_ACCESS_KEY`,
`MINIO_SECRET_KEY`, or `JWT_SIGNING_SECRET` is still at its
`changeme-local-only*` default — see
`docs/deployment/production-deployment.md`'s "Startup Now Refuses to
Boot on Default Secrets". This is not a bug: rotate the specific
variable named in the error message. If you see this in *local*
development, you've almost certainly set `ENVIRONMENT=production`
locally by mistake — it should be `development` or `testing`.

## The Backend Won't Start: `ConfigurationException: SECURITY_TRUSTED_HOSTS cannot be '*'` (or the CORS equivalent)

Same root cause as above, from Phase 1, Prompt 3 — a `staging`/
`production` `ENVIRONMENT` requires explicit values for
`SECURITY_TRUSTED_HOSTS`/`SECURITY_CORS_ALLOWED_ORIGINS`, never `*`.

## `docker build` Fails on `apps/backend/Dockerfile`

- **"pyproject.toml not found" / COPY failures** — you almost certainly
  ran `docker build` from `apps/backend/` instead of the repository
  root. The build context must include the root `pyproject.toml` too
  (uv's workspace resolution needs it) — see
  `docs/deployment/production-deployment.md`'s exact build command.
- **`uv sync` resolution failure** — no `uv.lock` is committed yet (see
  the Dockerfile's own header comment), so a build re-resolves
  dependencies against `apps/backend/pyproject.toml`'s declared ranges
  every time; a genuinely unresolvable range is a real dependency
  conflict to fix in that file, not a transient issue.
- **`--mount=type=cache` unsupported** — requires BuildKit (the default
  in any Docker version from the last several years). If you see a
  syntax error on that line specifically, your Docker installation has
  BuildKit disabled; enable it (`DOCKER_BUILDKIT=1` or Docker Desktop's
  settings) rather than removing the cache mount.

## The Backend Container Starts But Immediately Fails Its Healthcheck

`apps/backend/Dockerfile`'s `HEALTHCHECK` hits `GET /live` only (no
dependency check — see that Dockerfile's comment for why). If it's
failing, the process itself isn't coming up at all — check
`docker logs <container>` for a startup exception, most commonly one of
the `ConfigurationException`s above, or a bind-address/port conflict
with `BACKEND_HOST`/`BACKEND_PORT`.

## CI Fails on `black --check` / `isort --check-only` But Passes Locally

You ran `scripts/format.sh` (which formats in place) rather than
checking. Run the check-only form CI actually uses before pushing:

```bash
uv run black --check apps/backend
uv run isort --check-only apps/backend
```

`scripts/validate.sh` runs the same checks `.github/workflows/ci.yml`'s
`quality` job does — run it locally before pushing to avoid this
entirely.

## CI's `security` Job Fails on `pip-audit`

This job step is intentionally `continue-on-error: true` (see
`.github/workflows/ci.yml`'s comment) — a new CVE in a transitive
dependency is not something a given PR's author can always fix
immediately. The job step will show as failed but does not block merge;
triage the specific finding (upgrade the affected package, or confirm
it's not exploitable in this codebase's usage) as a follow-up.

## Still Stuck?

Check `scripts/doctor.sh` output, then `scripts/logs.sh <service>` for
the specific failing service, then this document's relevant section. If
none of the above applies, the issue is likely specific to your local
Docker installation — consult Docker's own documentation for your
platform.
