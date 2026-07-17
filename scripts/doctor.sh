#!/usr/bin/env bash
# Checks the health of every Cerebrum local infrastructure service.
# Exits non-zero if any service is unhealthy — safe to use in CI or as a
# pre-flight check before running tests.
#
# Usage: scripts/doctor.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

bash "${REPO_ROOT}/infrastructure/docker/healthchecks/check-all.sh"
