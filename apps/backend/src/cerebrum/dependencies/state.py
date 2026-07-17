"""The Application State dependency provider — a "Singleton" lifetime:
the same object, assembled once at startup (see
cerebrum.core.lifecycle), for the life of the process.
"""

from typing import Annotated

from fastapi import Depends, Request

from cerebrum.core.state import ApplicationState


def get_application_state(request: Request) -> ApplicationState:
    """Reads the state assembled during the lifespan's startup phase off
    ``request.app.state``. This is the one sanctioned place ``app.state``
    is accessed directly — everywhere else depends on
    :data:`ApplicationStateDep`.
    """
    state: ApplicationState = request.app.state.cerebrum
    return state


ApplicationStateDep = Annotated[ApplicationState, Depends(get_application_state)]
