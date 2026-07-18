"""Reusable serialization foundation for API schemas (CIS Phase 1 Prompt
6). Datetime, UUID, and Enum already serialize consistently through
Pydantic v2's own defaults (ISO-8601, ``str``, and the member's value,
respectively) whenever a model is dumped with ``mode="json"`` — see
cerebrum.core.exception_handlers's ``build_error_response`` for the
existing precedent. ``Decimal`` is the one type Pydantic does not
serialize losslessly by default (it can emit a ``float``, silently
losing precision); :data:`DecimalAsString` is this milestone's "Future
custom serializers" foundation for the first schema that needs one.

:class:`APIModel` is the shared base a future schema SHOULD inherit from
rather than ``pydantic.BaseModel`` directly, for ``from_attributes``
(so an ORM row can be returned straight from a route without a manual
field-by-field conversion) applied consistently. Existing schemas
(``envelope``, ``health``, ``auth``) predate this milestone and are left
on plain ``BaseModel`` rather than migrated without cause — see
docs/architecture/coding-guidelines.md's "No Premature Abstraction":
they work today and gain nothing from the change.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer


class APIModel(BaseModel):
    """Base class for future API request/response schemas."""

    model_config = ConfigDict(from_attributes=True)


DecimalAsString = Annotated[
    Decimal, PlainSerializer(lambda value: str(value), return_type=str)
]
"""A ``Decimal`` field that serializes to its exact string form (e.g.
``"19.99"``, never ``19.990000000000002``) — the standard way to expose a
monetary or otherwise precision-sensitive value over JSON, which has no
native arbitrary-precision decimal type.
"""
