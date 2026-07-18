"""Application-layer DTOs for the authentication use cases — distinct
from ``cerebrum.api.schemas.auth``'s Pydantic request/response models.
An application service returns/accepts these, never a Pydantic model
from the presentation layer, per docs/architecture/dependency-rules.md
(application/ never depends on api/). ``cerebrum.api.v1.auth`` adapts
between the two.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenPair:
    """The result of a successful login or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    """Access token lifetime in seconds — echoes
    ``SecuritySettings.access_token_expire_minutes`` so a client doesn't
    need its own copy of that configuration to know when to refresh.
    """
