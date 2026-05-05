"""Facade no-op contract tests.

The contract this file protects: when telemetry is disabled (the default),
the facade functions in `blunder_tutor.observability` do not raise and do
not call into `sentry_sdk`. Call sites can be sprinkled across services
without conditional `if telemetry_enabled` guards because of this guarantee.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from blunder_tutor.observability import (
    Span,
    count,
    distribution,
    gauge,
    sentry_init,
    start_span,
)
from blunder_tutor.observability import metrics as metrics_facade
from blunder_tutor.observability import tracing as tracing_facade


@pytest.fixture(autouse=True)
def _facade_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sentry_init, "active", False)


class TestMetricsFacadeWhenInactive:
    def test_count_does_not_call_sentry(self) -> None:
        with patch.object(metrics_facade.sentry_sdk, "metrics") as sentry_metrics:
            count("engine.analyse.completed", tags={"outcome": "ok"})
            assert not sentry_metrics.count.called

    def test_gauge_does_not_call_sentry(self) -> None:
        with patch.object(metrics_facade.sentry_sdk, "metrics") as sentry_metrics:
            gauge("ws.connections.active", 7)
            assert not sentry_metrics.gauge.called

    def test_distribution_does_not_call_sentry(self) -> None:
        with patch.object(metrics_facade.sentry_sdk, "metrics") as sentry_metrics:
            distribution("engine.analyse.duration_ms", 12.5)
            assert not sentry_metrics.distribution.called

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("count", {"name": "x"}),
            ("count", {"name": "x", "value": 5, "tags": {"k": "v"}}),
            ("gauge", {"name": "x", "value": 1.0}),
            ("distribution", {"name": "x", "value": 1.0}),
        ],
    )
    def test_no_call_returns_none(self, name: str, kwargs: dict) -> None:
        funcs = {"count": count, "gauge": gauge, "distribution": distribution}
        assert funcs[name](**kwargs) is None


class TestStartSpanWhenInactive:
    def test_yields_span_object(self) -> None:
        with start_span("engine.analyse", op="chess.engine") as span:
            assert isinstance(span, Span)

    def test_set_tag_is_noop(self) -> None:
        with start_span("x") as span:
            span.set_tag("depth", 20)

    def test_set_data_is_noop(self) -> None:
        with start_span("x") as span:
            span.set_data("correlation_id", "abc-123")

    def test_does_not_call_sentry_start_span(self) -> None:
        with (
            patch.object(tracing_facade.sentry_sdk, "start_span") as sentry_start,
            start_span("x", op="y") as span,
        ):
            span.set_tag("k", "v")
            span.set_data("d", 1)
            assert not sentry_start.called


class TestFacadeWhenActive:
    """Once `set_active(True)` flips the state, the facade forwards to sentry_sdk."""

    def test_count_forwards_to_sentry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sentry_init, "active", True)
        with patch.object(metrics_facade.sentry_sdk, "metrics") as sentry_metrics:
            count("job.completed", value=1, tags={"kind": "sync_games"})
            sentry_metrics.count.assert_called_once_with(
                "job.completed", 1, attributes={"kind": "sync_games"}
            )

    def test_gauge_forwards_to_sentry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sentry_init, "active", True)
        with patch.object(metrics_facade.sentry_sdk, "metrics") as sentry_metrics:
            gauge("ws.connections.active", 12.0, tags=None)
            sentry_metrics.gauge.assert_called_once_with(
                "ws.connections.active", 12.0, attributes=None
            )

    def test_distribution_forwards_to_sentry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sentry_init, "active", True)
        with patch.object(metrics_facade.sentry_sdk, "metrics") as sentry_metrics:
            distribution("engine.analyse.duration_ms", 15.5, tags={"depth": "20"})
            sentry_metrics.distribution.assert_called_once_with(
                "engine.analyse.duration_ms", 15.5, attributes={"depth": "20"}
            )
