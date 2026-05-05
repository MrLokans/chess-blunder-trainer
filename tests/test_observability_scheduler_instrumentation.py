"""Smoke test: scheduler tick is decorated with `@sentry_sdk.monitor`
and runs cleanly when Sentry is not initialized.

We do not assert on Sentry-side check-in semantics — that is the SDK's
contract. We assert on (1) the decoration is present, (2) the wrapped
function still walks an empty user list without raising under the
default test-suite state where Sentry is inactive.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from blunder_tutor.background import scheduler as scheduler_module


class TestSchedulerCronsDecoration:
    def test_fanout_tick_carries_sentry_monitor_wrapper(self) -> None:
        # `sentry_sdk.monitor` uses functools.wraps internally, exposing
        # the original via `__wrapped__`. Presence of that attribute is
        # the cheapest probe that the decorator is in place.
        assert hasattr(scheduler_module._fanout_tick, "__wrapped__"), (
            "_fanout_tick must be wrapped by @sentry_sdk.monitor"
        )

    async def test_fanout_tick_runs_clean_with_sentry_disabled(self) -> None:
        list_users = AsyncMock(return_value=[])

        await scheduler_module._fanout_tick(
            event_bus=AsyncMock(),
            engine_path="/fake/stockfish",
            list_users=list_users,
            db_path_resolver=lambda _uid: None,
        )

        list_users.assert_awaited_once()
