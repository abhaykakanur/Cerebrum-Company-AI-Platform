# ==============================================================================
# Cerebrum Backend — Production Container Image
# ==============================================================================
#
# Multi-stage build: `builder` resolves dependencies and installs the
# package with uv into a virtual environment; `runtime` copies only that
# venv and the application source into a slim, non-root final image —
# the shipped image never contains uv, pip, or build tooling.
#
# Build from the REPOSITORY ROOT (both pyproject.toml files must be in
# the build context):
#   docker build -f apps/backend/Dockerfile -t cerebrum-backend \
#     --build-arg BUILD_COMMIT=$(git rev-parse HEAD) \
#     --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
#     .
#
# See docs/deployment/production-deployment.md for the full deployment
# guide. docs/deployment/docker-architecture.md covers
# infrastructure/docker/docker-compose.yml's local *datastore* services
# — a separate concern from this application image, which those
# datastores support but do not define.
#
# No uv.lock exists in this repository yet (see this Dockerfile's
# entry in docs/deployment/troubleshooting.md) — dependency versions are
# re-resolved against each dependency's declared range on every build,
# per apps/backend/pyproject.toml, rather than pinned to an exact,
# reproducible set. Generating and committing one is a recommended
# follow-up, not a defect blocking this image's use today.
# ==============================================================================

# ---- Builder ------------------------------------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# The root workspace pyproject.toml is required too: apps/backend's own
# pyproject.toml inherits [tool.black]/[tool.ruff]/[tool.isort]/[tool.mypy]
# from it via uv's workspace resolution — see that file's closing
# comment. Dependencies are installed before application source is
# copied in, so a source-only change doesn't invalidate this (expensive)
# dependency-resolution layer in Docker's build cache.
COPY pyproject.toml ./pyproject.toml
COPY apps/backend/pyproject.toml apps/backend/pyproject.toml
COPY apps/backend/README.md apps/backend/README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    cd apps/backend && uv sync --no-dev --no-install-project

COPY apps/backend/src apps/backend/src

RUN --mount=type=cache,target=/root/.cache/uv \
    cd apps/backend && uv sync --no-dev

# ---- Runtime --------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Build provenance, surfaced on GET /health — see
# cerebrum.config.application.ApplicationSettings.build_commit/build_time.
# Left at their "unknown" default if the build command above doesn't
# pass them (e.g. a local `docker build` without the extra flags).
ARG BUILD_COMMIT=unknown
ARG BUILD_TIME=unknown
ENV BUILD_COMMIT=${BUILD_COMMIT} \
    BUILD_TIME=${BUILD_TIME} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/apps/backend/.venv/bin:${PATH}"

# A dedicated, unprivileged user — this process never needs root, and
# running as root inside a container is an avoidable blast-radius
# increase, per docs/architecture/specification/79_Threat_Model.md.
RUN groupadd --system cerebrum && \
    useradd --system --gid cerebrum --create-home --home-dir /home/cerebrum cerebrum

WORKDIR /app

# Copied at the SAME absolute path (/app/apps/backend/...) used in the
# builder stage: uv's editable install of the `cerebrum` package points
# at that path, and copying it anywhere else would silently break
# imports at container start rather than at build time.
COPY --from=builder --chown=cerebrum:cerebrum /app/apps/backend/.venv apps/backend/.venv
COPY --from=builder --chown=cerebrum:cerebrum /app/apps/backend/src apps/backend/src

USER cerebrum

EXPOSE 8000

# Matches cerebrum.api.health's Liveness Check semantics exactly — no
# dependency check, only "is this process running and not deadlocked."
# See docs/architecture/specification/38_Observability.md's Health
# Checks table for why this deliberately does NOT probe /ready or
# /health (an orchestrator's own readiness probe should hit /ready
# separately; baking a dependency check into the container healthcheck
# would restart a perfectly-alive process over a transient database
# blip, per cerebrum.core.lifecycle's graceful-degradation design).
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request as u, sys; sys.exit(0 if u.urlopen('http://localhost:8000/live', timeout=3).status == 200 else 1)"

# BACKEND_HOST/BACKEND_PORT (see .env.example, cerebrum.config.api.APISettings)
# already default to 0.0.0.0:8000 — no --host/--port flags are hardcoded
# here beyond matching that default, since uvicorn is invoked directly
# rather than through cerebrum.main.run() (whose --reload switch is a
# development-only convenience this image deliberately never enables).
CMD ["python", "-m", "uvicorn", "cerebrum.main:app", "--host", "0.0.0.0", "--port", "8000"]
