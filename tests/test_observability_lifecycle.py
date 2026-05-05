"""Lifecycle wiring tests for opt-in observability.

Verifies that `_run_startup` calls `init_observability` *before* any other
startup work (so subsequent failures land in Sentry) and that
`_run_shutdown` calls `shutdown_observability` last (so a flush stall
cannot prevent other cleanup). The Sentry transport is never started —
the SDK boundary (`sentry_sdk.init` / `sentry_sdk.flush`) is patched and
inspected.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.observability import sentry_init
from blunder_tutor.observability.config import ObservabilityConfig
from blunder_tutor.web.app import create_app
from blunder_tutor.web.app_lifecycle import _run_shutdown, _run_startup
from blunder_tutor.web.config import AppConfig
from tests.helpers.engine import mock_engine_context

_TEST_DSN = "https://abc@example.ingest.sentry.io/123"


@pytest.fixture(autouse=True)
def _reset_observability_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sentry_init, "active", False)


def _enable_observability(config: AppConfig) -> AppConfig:
    return config.model_copy(
        update={
            "observability": ObservabilityConfig(
                sentry_enabled=True,
                sentry_dsn=_TEST_DSN,
            ),
        },
    )


class TestLifecycleWithDisabledObservability:
    def test_startup_and_shutdown_do_not_call_sentry_sdk(
        self, test_config: AppConfig
    ) -> None:
        with (
            mock_engine_context(),
            patch.object(sentry_init.sentry_sdk, "init") as init_mock,
            patch.object(sentry_init.sentry_sdk, "flush") as flush_mock,
            TestClient(create_app(test_config)),
        ):
            pass
        assert not init_mock.called
        assert not flush_mock.called


class TestLifecycleWithEnabledObservability:
    def test_startup_invokes_sentry_init_once(self, test_config: AppConfig) -> None:
        config = _enable_observability(test_config)
        with (
            mock_engine_context(),
            patch.object(sentry_init.sentry_sdk, "init") as init_mock,
            patch.object(sentry_init.sentry_sdk, "flush"),
            TestClient(create_app(config)),
        ):
            pass
        assert init_mock.call_count == 1

    def test_shutdown_invokes_sentry_flush_once(self, test_config: AppConfig) -> None:
        config = _enable_observability(test_config)
        with (
            mock_engine_context(),
            patch.object(sentry_init.sentry_sdk, "init"),
            patch.object(sentry_init.sentry_sdk, "flush") as flush_mock,
            TestClient(create_app(config)),
        ):
            pass
        assert flush_mock.call_count == 1


class TestStartupExceptionPropagation:
    async def test_failure_after_init_propagates_with_init_already_called(
        self, test_config: AppConfig
    ) -> None:
        """An exception in `coordinator.start()` (the statement immediately
        after `init_observability`) must propagate, and Sentry must have
        already been initialized so the failure is captured.
        """
        config = _enable_observability(test_config)
        with (
            mock_engine_context(),
            patch.object(sentry_init.sentry_sdk, "init") as init_mock,
        ):
            app = create_app(config)
            boom = AsyncMock(side_effect=RuntimeError("startup boom"))
            with (
                patch.object(app.state.work_coordinator, "start", boom),
                pytest.raises(RuntimeError, match="startup boom"),
            ):
                await _run_startup(app)
            assert init_mock.call_count == 1


def _stub_started_app() -> SimpleNamespace:
    """Minimal stand-in for an app whose `_run_startup` has completed.

    `_run_shutdown` only reads attributes on `app.state`, so a
    `SimpleNamespace` with the right surface is enough to exercise the
    cleanup ordering and the `try/finally` guard around
    `shutdown_observability`.
    """
    return SimpleNamespace(
        state=SimpleNamespace(
            cache_invalidator=MagicMock(stop=AsyncMock()),
            job_executor=MagicMock(shutdown=AsyncMock()),
            scheduler=MagicMock(shutdown=MagicMock()),
            work_coordinator=MagicMock(shutdown=AsyncMock()),
            settings_repo=None,
            auth=None,
        ),
    )


class TestShutdownExceptionGuard:
    async def test_flush_runs_even_when_earlier_cleanup_step_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Spec: `shutdown_observability` must run as the last statement
        of `_run_shutdown` so that exceptions raised during cleanup are
        still captured. A bare sequential chain would skip the flush as
        soon as any earlier `await` raises; the `try/finally` guard is
        what upholds the contract.
        """
        monkeypatch.setattr(sentry_init, "active", True)
        app = _stub_started_app()
        app.state.cache_invalidator.stop = AsyncMock(
            side_effect=RuntimeError("cleanup boom")
        )
        with patch.object(sentry_init.sentry_sdk, "flush") as flush_mock:
            with pytest.raises(RuntimeError, match="cleanup boom"):
                await _run_shutdown(app)
            assert flush_mock.call_count == 1
