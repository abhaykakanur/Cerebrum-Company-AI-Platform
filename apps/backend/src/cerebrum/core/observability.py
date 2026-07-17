"""Metrics and tracing extension points.

CIS Phase 1 Prompt 3 Section 2/3 asks for Metrics and Tracer placeholders
and for observability hooks to exist without any external integration
yet. ``MetricsRegistry`` and ``Tracer`` below are Protocols a future
Prometheus/OpenTelemetry adapter implements; :class:`NoOpMetricsRegistry`
and :class:`NoOpTracer` are the only implementations that exist today,
wired into :class:`~cerebrum.core.state.ApplicationState` so every call
site that will eventually record a real metric or span can be written
now against the final interface.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol


class MetricsRegistry(Protocol):
    """The instrumentation port for Counters, Gauges, and Histograms —
    see docs/architecture/specification/38_Observability.md's Metrics
    section. Metric names follow the ``<component>_<domain>_<measurement>``
    convention that document establishes; this Protocol does not enforce
    naming, only the recording operations.
    """

    def increment_counter(
        self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None: ...

    def set_gauge(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None: ...

    def observe_histogram(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None: ...


class Tracer(Protocol):
    """The instrumentation port for distributed tracing spans — see
    docs/architecture/specification/38_Observability.md's Distributed
    Tracing section (future OpenTelemetry backend).
    """

    @contextmanager
    def start_span(self, name: str) -> Iterator[None]: ...


class NoOpMetricsRegistry:
    """Records nothing. Satisfies :class:`MetricsRegistry` so every call
    site behaves identically whether or not a real backend is configured
    — see docs/architecture/specification/38_Observability.md's "No
    external integration yet" scope for this milestone.
    """

    def increment_counter(
        self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        return None

    def set_gauge(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        return None

    def observe_histogram(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        return None


class NoOpTracer:
    """Opens spans that record nothing and propagate nothing."""

    @contextmanager
    def start_span(self, name: str) -> Iterator[None]:
        yield None
