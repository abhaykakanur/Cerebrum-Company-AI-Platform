"""Application configuration loading: environment variables and
configuration-file parsing into validated, typed settings objects.

See docs/architecture/specification/37_Configuration_Strategy.md. Secrets
are explicitly NOT loaded here — see infrastructure/ for the Security
Domain's GetSecret port and its adapters.
"""

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walks upward from ``start`` for the workspace-root marker
    (``pnpm-workspace.yaml`` — unambiguous, present only at the
    repository root). Falls back to ``start`` itself if the marker
    isn't found (e.g. a context where this source tree has been copied
    out of the monorepo), so a missing marker degrades to the old
    CWD-relative lookup rather than raising at import time.
    """
    for candidate in (start, *start.parents):
        if (candidate / "pnpm-workspace.yaml").is_file():
            return candidate
    return start


# The repository root's .env file, resolved from this module's own file
# location rather than the launching process's current working
# directory. Every Settings subclass in this package used to declare a
# bare `env_file=".env"`, which pydantic-settings resolves relative to
# CWD — harmless when a process happens to be launched from the
# repository root, but silently wrong for this project's own documented
# workflow of running alembic/uvicorn/scripts from `apps/backend/`
# (see docs/deployment/production-deployment.md's "Database Migrations"
# section), which has no `.env` of its own. In that case every setting
# silently fell back to its hardcoded placeholder default (e.g.
# `POSTGRES_USER="cerebrum"`) instead of raising — see
# docs/deployment/troubleshooting.md. Anchoring to `__file__` (via the
# workspace-root marker, not a fixed `.parent` count that would silently
# break if this package's depth in the tree ever changes) makes the
# lookup CWD-independent, the same fix already applied to
# `scripts/_common.sh`'s `REPO_ROOT`.
ENV_FILE = _find_repo_root(Path(__file__).resolve()) / ".env"
