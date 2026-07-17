#!/usr/bin/env bash
# Runs the full local validation suite in the same order as the CI/CD
# pipeline's fast static-check stages
# (docs/architecture/specification/97_CICD_Architecture.md, stages 1-6):
# formatting check, lint, type check, unit tests. Intended as a pre-push
# sanity check.
#
# Usage: scripts/validate.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

cerebrum::log "Step 1/4 — Format check..."
(cd "${REPO_ROOT}" && uv run black --check apps/backend && uv run isort --check-only apps/backend)
(cd "${REPO_ROOT}" && pnpm run format:check)

cerebrum::log "Step 2/4 — Lint..."
"${REPO_ROOT}/scripts/lint.sh"

cerebrum::log "Step 3/4 — Type check..."
"${REPO_ROOT}/scripts/typecheck.sh"

cerebrum::log "Step 4/4 — Unit tests..."
"${REPO_ROOT}/scripts/test.sh"

cerebrum::log "Validation passed. Safe to push."
