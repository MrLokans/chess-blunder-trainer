"""Init wiring tests.

Verifies `init_observability` constructs `sentry_sdk.init` with the right
parameters, that calling it twice is idempotent, and that the
`_traces_sampler` closure drops noise paths correctly. The actual Sentry
transport is never started — these are parameter-inspection tests only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.scrubber import EventScrubber

from blunder_tutor.observability import sentry_init
from blunder_tutor.observability.config import ObservabilityConfig
from blunder_tutor.observability.scrubbing import PROJECT_DENYLIST
from blunder_tutor.observability.sentry_init import (
    _build_traces_sampler,
    init_observability,
    shutdown_observability,
)

_TEST_DSN = "https://abc@example.ingest.sentry.io/123"

_TracesSampler = Callable[[dict[str, Any]], float]


def _enabled_config(**overrides: Any) -> ObservabilityConfig:
    return ObservabilityConfig(
        sentry_enabled=True,
        sentry_dsn=_TEST_DSN,
        **overrides,
    )


@pytest.fixture(autouse=True)
def _reset_observability_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sentry_init, "active", False)


class TestInitObservabilityWhenDisabled:
    def test_disabled_config_does_not_call_sentry_init(self) -> None:
        config = ObservabilityConfig()  # default disabled
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            assert not sentry_init_mock.called

    def test_disabled_config_leaves_facade_inactive(self) -> None:
        config = ObservabilityConfig()
        with patch.object(sentry_init.sentry_sdk, "init"):
            init_observability(config)
            assert sentry_init.active is False


class TestInitObservabilityWhenEnabled:
    def test_calls_sentry_init_with_dsn(self) -> None:
        config = _enabled_config(sentry_environment="staging")
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            kwargs = sentry_init_mock.call_args.kwargs
            assert kwargs["dsn"] == _TEST_DSN
            assert kwargs["environment"] == "staging"

    def test_passes_release_when_set(self) -> None:
        config = _enabled_config(sentry_release="abc1234")
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            assert sentry_init_mock.call_args.kwargs["release"] == "abc1234"

    def test_passes_traces_sample_rate(self) -> None:
        config = _enabled_config(traces_sample_rate=0.25)
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            assert sentry_init_mock.call_args.kwargs["traces_sample_rate"] == 0.25

    def test_constructs_event_scrubber_with_project_denylist(self) -> None:
        config = _enabled_config()
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            scrubber = sentry_init_mock.call_args.kwargs["event_scrubber"]
            assert isinstance(scrubber, EventScrubber)
            assert scrubber.recursive is True
            for project_key in PROJECT_DENYLIST:
                assert project_key in scrubber.denylist

    def test_includes_all_default_integrations(self) -> None:
        config = _enabled_config()
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            integration_types = {
                type(integration)
                for integration in sentry_init_mock.call_args.kwargs["integrations"]
            }
            assert FastApiIntegration in integration_types
            assert StarletteIntegration in integration_types
            assert HttpxIntegration in integration_types
            assert AsyncioIntegration in integration_types
            assert LoggingIntegration in integration_types

    def test_passes_send_default_pii(self) -> None:
        config = _enabled_config(send_default_pii=True)
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            assert sentry_init_mock.call_args.kwargs["send_default_pii"] is True

    def test_flips_active_flag_after_init(self) -> None:
        config = _enabled_config()
        with patch.object(sentry_init.sentry_sdk, "init"):
            init_observability(config)
            assert sentry_init.active is True


class TestIdempotency:
    def test_second_call_is_noop(self) -> None:
        config = _enabled_config()
        with patch.object(sentry_init.sentry_sdk, "init") as sentry_init_mock:
            init_observability(config)
            init_observability(config)
            assert sentry_init_mock.call_count == 1

    def test_shutdown_after_init_resets_state(self) -> None:
        config = _enabled_config()
        with (
            patch.object(sentry_init.sentry_sdk, "init"),
            patch.object(sentry_init.sentry_sdk, "flush") as flush_mock,
        ):
            init_observability(config)
            shutdown_observability()
            flush_mock.assert_called_once_with(timeout=2.0)
            assert sentry_init.active is False

    def test_shutdown_without_init_is_noop(self) -> None:
        with patch.object(sentry_init.sentry_sdk, "flush") as flush_mock:
            shutdown_observability()
            assert not flush_mock.called


class TestTracesSampler:
    @pytest.fixture
    def sampler(self) -> _TracesSampler:
        return _build_traces_sampler(0.5, trace_health=False)

    @pytest.mark.parametrize(
        "noise_path",
        ["/health", "/favicon.ico", "/static/css/x.css", "/static/js/app.js"],
    )
    def test_drops_noise_paths(
        self,
        sampler: _TracesSampler,
        noise_path: str,
    ) -> None:
        assert sampler({"asgi_scope": {"path": noise_path}}) == 0.0

    @pytest.mark.parametrize(
        "real_path",
        ["/api/puzzle", "/api/games", "/dashboard", "/trainer"],
    )
    def test_uses_configured_rate_for_real_paths(
        self,
        sampler: _TracesSampler,
        real_path: str,
    ) -> None:
        assert sampler({"asgi_scope": {"path": real_path}}) == 0.5

    def test_trace_health_includes_health_endpoint(self) -> None:
        sampler = _build_traces_sampler(0.5, trace_health=True)
        assert sampler({"asgi_scope": {"path": "/health"}}) == 0.5
        assert sampler({"asgi_scope": {"path": "/static/x"}}) == 0.5

    def test_zero_rate_returns_zero_for_real_paths(self) -> None:
        sampler = _build_traces_sampler(0.0, trace_health=False)
        assert sampler({"asgi_scope": {"path": "/api/puzzle"}}) == 0.0

    def test_zero_rate_drops_noise_too(self) -> None:
        sampler = _build_traces_sampler(0.0, trace_health=False)
        assert sampler({"asgi_scope": {"path": "/health"}}) == 0.0

    def test_parent_sampled_true_overrides_configured_rate(self) -> None:
        sampler = _build_traces_sampler(0.1, trace_health=False)
        decision = sampler(
            {"asgi_scope": {"path": "/api/x"}, "parent_sampled": True},
        )
        assert decision == 1.0

    def test_parent_sampled_false_drops_trace(self) -> None:
        # Honor parent's "no" decision rather than up-sampling via the
        # configured rate. See the comment in `_build_traces_sampler`.
        sampler = _build_traces_sampler(1.0, trace_health=False)
        decision = sampler(
            {"asgi_scope": {"path": "/api/x"}, "parent_sampled": False},
        )
        assert decision == 0.0

    def test_missing_asgi_scope_uses_configured_rate(self) -> None:
        sampler = _build_traces_sampler(0.5, trace_health=False)
        assert sampler({}) == 0.5
