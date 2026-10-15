"""Facade over the Sentry SDK so call sites never import it; every function is a no-op when
telemetry is disabled (the default)."""

from __future__ import annotations

from blunder_tutor.observability.metrics import count, distribution, gauge
from blunder_tutor.observability.sentry_init import (
    init_observability,
    shutdown_observability,
)
from blunder_tutor.observability.tracing import Span, start_span

__all__ = [
    "Span",
    "count",
    "distribution",
    "gauge",
    "init_observability",
    "shutdown_observability",
    "start_span",
]
