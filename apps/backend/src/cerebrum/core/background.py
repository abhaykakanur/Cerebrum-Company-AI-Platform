"""Background Runtime registration — the Application Factory's
explicit-but-currently-empty startup stage.

CIS Phase 1 Prompt 3 Section 2 lists "Background Runtime Registration"
among the factory's owned responsibilities, and Section 2's Startup
Pipeline names it as its own stage. cerebrum.workers defines Worker/Job/
Queue/Scheduler interfaces only — "No concrete implementations" — so
there is nothing to start yet. This function exists so that stage is
explicit and traceable rather than silently absent, per this milestone's
Implementation Principles ("Hidden initialization is prohibited").
"""

from fastapi import FastAPI

from cerebrum.config.settings import Settings
from cerebrum.core.logging import get_logger

_logger = get_logger("cerebrum.core")


def register_background_runtime(app: FastAPI, settings: Settings) -> None:
    if not settings.worker.enabled:
        _logger.info(
            "background_runtime.registration_skipped",
            reason="WORKER_ENABLED is false; no worker implementation exists at "
            "this milestone.",
        )
        return
    # WORKER_ENABLED=true has no effect yet — flipping it on cannot start
    # a runtime that does not exist. A future phase's concrete Worker
    # implementations (cerebrum.workers) are wired in here.
    _logger.warning(
        "background_runtime.enabled_but_unimplemented",
        reason="WORKER_ENABLED is true, but no concrete worker runtime exists yet.",
    )
