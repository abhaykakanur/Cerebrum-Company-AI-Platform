"""Request/response schemas for ``cerebrum.api.v1.auth``.

``TokenResponse`` is deliberately the flat OAuth2 token shape
(``access_token``/``token_type``/``expires_in``/``refresh_token``), not
wrapped in :class:`~cerebrum.api.schemas.envelope.SuccessResponse` — both
the OAuth2 Password Flow spec and Swagger UI's built-in "Authorize"
popup (which parses this exact shape from the token endpoint's response
to populate subsequent "Try it out" calls) require it unwrapped. See
``cerebrum.api.health``'s response models for the existing precedent of
returning a plain model rather than the generic envelope — no endpoint
in this codebase uses that envelope yet.
"""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenResponse(BaseModel):
    """The OAuth2 Password Flow token response shape."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 900,
                }
            ]
        }
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime, in seconds.")


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class CurrentUserResponse(BaseModel):
    """ "Current User Dependency" surfaced over HTTP — see
    cerebrum.dependencies.auth.get_current_user.
    """

    id: uuid.UUID
    email: EmailStr
    organization_id: uuid.UUID
    is_active: bool
    is_verified: bool
