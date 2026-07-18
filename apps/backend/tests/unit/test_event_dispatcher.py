"""Proves CIS Phase 1 Prompt 7's Testing improvement: the in-process
:class:`~cerebrum.events.dispatcher.EventDispatcher` had a real, working
publish/subscribe implementation with zero test coverage — no concrete
business event uses it yet (see that module's docstring), but the
mechanism itself is real code that deserves the same coverage as
anything else in this codebase.
"""

import pytest

from cerebrum.events.base import DomainEvent
from cerebrum.events.dispatcher import EventDispatcher

pytestmark = pytest.mark.unit


class _WidgetCreated(DomainEvent):
    pass


class _OtherEvent(DomainEvent):
    pass


def _widget_created(widget_id: str = "w-1") -> _WidgetCreated:
    return _WidgetCreated(event_type="widget.created")


def test_publish_with_no_subscribers_does_not_raise() -> None:
    dispatcher = EventDispatcher()
    dispatcher.publish(_widget_created())  # must not raise


def test_subscribed_handler_is_called_with_the_event() -> None:
    dispatcher = EventDispatcher()
    received: list[DomainEvent] = []
    dispatcher.subscribe(_WidgetCreated, received.append)

    event = _widget_created()
    dispatcher.publish(event)

    assert received == [event]


def test_multiple_handlers_for_the_same_event_are_all_called() -> None:
    dispatcher = EventDispatcher()
    calls: list[str] = []
    dispatcher.subscribe(_WidgetCreated, lambda e: calls.append("first"))
    dispatcher.subscribe(_WidgetCreated, lambda e: calls.append("second"))

    dispatcher.publish(_widget_created())

    assert calls == ["first", "second"]


def test_handler_is_not_called_for_a_different_event_type() -> None:
    dispatcher = EventDispatcher()
    received: list[DomainEvent] = []
    dispatcher.subscribe(_WidgetCreated, received.append)

    dispatcher.publish(_OtherEvent(event_type="other.event"))

    assert received == []


def test_each_dispatcher_instance_has_independent_subscriptions() -> None:
    first = EventDispatcher()
    second = EventDispatcher()
    received: list[DomainEvent] = []
    first.subscribe(_WidgetCreated, received.append)

    second.publish(_widget_created())

    assert received == []
