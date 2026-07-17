"""The in-process event dispatcher realizing the Event-Driven-Ready
pattern — see docs/architecture/specification/34_Architecture_Principles.md
("events are raised and consumed synchronously, in-process, in V1.0; a
message-broker-backed dispatcher is a future infrastructure adapter swap,
not a redesign of this package's contracts").

No concrete business event is subscribed to anything here; this module
provides the mechanism, not a policy. A future domain calls
``dispatcher.subscribe(SomeEvent, some_handler)`` during its own startup
wiring.
"""

from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

from cerebrum.core.logging import get_events_logger
from cerebrum.events.base import DomainEvent

EventT = TypeVar("EventT", bound=DomainEvent)
EventHandler = Callable[[EventT], None]

_logger = get_events_logger()


class EventDispatcher:
    """Synchronous, in-process publish/subscribe. Not thread-safe beyond
    what the single-process, single-event-loop ASGI model already
    guarantees — a future message-broker-backed adapter takes on that
    concern when it replaces this implementation, per the
    Event-Driven-Ready principle above.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[DomainEvent]]] = (
            defaultdict(list)
        )

    def subscribe(
        self, event_type: type[EventT], handler: EventHandler[EventT]
    ) -> None:
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        _logger.debug(
            "event.published",
            event_type=event.event_type,
            event_id=str(event.event_id),
            handler_count=len(handlers),
        )
        for handler in handlers:
            handler(event)
