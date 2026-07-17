"""Domain event definitions and the in-process event dispatch mechanism
realizing the Event-Driven-Ready pattern.

See docs/architecture/specification/34_Architecture_Principles.md
(Event-Driven-Ready — events are raised and consumed synchronously,
in-process, in V1.0; a message-broker-backed dispatcher is a future
infrastructure adapter swap, not a redesign of this package's contracts).
"""
