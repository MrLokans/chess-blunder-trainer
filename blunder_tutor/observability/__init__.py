"""Opt-in observability — Sentry SDK behind a thin facade.

Call sites import only from this package; the underlying SDK can be
swapped (or augmented with OpenTelemetry) without changing a single
service or handler. When telemetry is disabled (the default), every
function in this package is a zero-cost no-op.
"""

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
