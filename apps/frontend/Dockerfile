# ==============================================================================
# Cerebrum Frontend — Production Container Image
# ==============================================================================
#
# Multi-stage build mirroring apps/backend/Dockerfile's convention: a
# `builder` stage resolves the pnpm workspace and produces a Next.js
# "standalone" output (next.config.js's `output: "standalone"`); the
# `runtime` stage copies only that pruned output — not the full
# node_modules tree or build tooling — into a slim, non-root final image.
#
# Build from the REPOSITORY ROOT (the pnpm workspace spans apps/frontend
# and packages/*, so the build context must include all of it):
#   docker build -f apps/frontend/Dockerfile -t cerebrum-frontend .
#
# See docs/deployment/production-deployment.md for the full deployment
# guide and infrastructure/docker/docker-compose.apps.yml for how this
# image is wired together with the backend and datastores.
# ==============================================================================

# ---- Builder ------------------------------------------------------------
FROM node:20-slim AS builder

# Matches the root package.json's "packageManager" field exactly — pnpm
# version drift between local dev and this image is what corepack exists
# to prevent.
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

WORKDIR /app

# Manifests only, first — every workspace package.json plus the lockfile,
# so `pnpm install` is cached independently of application source changes
# (identical reasoning to the backend Dockerfile's dependency-layer split).
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/frontend/package.json apps/frontend/package.json
COPY packages/eslint-config/package.json packages/eslint-config/package.json
COPY packages/shared-config/package.json packages/shared-config/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
COPY packages/shared-utils/package.json packages/shared-utils/package.json
COPY packages/tsconfig/package.json packages/tsconfig/package.json

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY apps/frontend apps/frontend
COPY packages packages

# NEXT_PUBLIC_* variables are inlined into the client bundle at build
# time, not read at container start — must be supplied as build args for
# a non-default backend origin (see docs/deployment/environment-variables.md).
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN pnpm --filter @cerebrum/frontend build

# ---- Runtime --------------------------------------------------------------
FROM node:20-slim AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# A dedicated, unprivileged user — matches apps/backend/Dockerfile's
# threat-model reasoning (docs/architecture/specification/79_Threat_Model.md).
RUN groupadd --system cerebrum && \
    useradd --system --gid cerebrum --create-home --home-dir /home/cerebrum cerebrum

WORKDIR /app

# `standalone` output already contains a pruned node_modules with only
# the packages actually imported at runtime — no separate `pnpm install`
# happens in this stage.
COPY --from=builder --chown=cerebrum:cerebrum /app/apps/frontend/.next/standalone ./
COPY --from=builder --chown=cerebrum:cerebrum /app/apps/frontend/.next/static ./apps/frontend/.next/static
COPY --from=builder --chown=cerebrum:cerebrum /app/apps/frontend/public ./apps/frontend/public

USER cerebrum

EXPOSE 3000

# No dependency checks (matches the backend image's liveness-only
# convention) — this process serves static/SSR pages independent of
# backend availability; the backend's own reachability is the browser's
# concern via NEXT_PUBLIC_API_BASE_URL, not this container's.
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/', (r) => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "apps/frontend/server.js"]
