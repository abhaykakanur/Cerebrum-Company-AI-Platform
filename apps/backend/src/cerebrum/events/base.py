"""``DomainEvent``: the base contract every future concrete domain event
inherits from. No concrete business event (e.g. ``UserCreated``,
``DocumentIngested``) is defined here — those belong to the domain that
raises them, in a future phase — see this milestone's Non-Objectives.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from cerebrum.utils.clock import utcnow


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Immutable base for every domain event. Subclasses add their own
    payload fields; every subclass inherits ``event_id``, ``event_type``,
    and ``occurred_at`` for free.
    """

    event_type: str
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utcnow)
