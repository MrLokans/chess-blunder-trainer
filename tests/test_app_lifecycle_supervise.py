from __future__ import annotations

import asyncio
import contextlib
import logging

from blunder_tutor.web import app_lifecycle


class TestSupervise:
    """A long-lived background task spawned bare with `create_task` makes a
    crash invisible — asyncio only surfaces it on GC, which never happens
    for a process-lifetime task. `_supervise` turns any exit into a log.
    """

    async def _settle(self, task: asyncio.Task) -> None:
        await asyncio.wait({task})
        await asyncio.sleep(0)  # let the done-callback run

    async def test_crash_is_logged(self, caplog) -> None:
        async def boom() -> None:
            raise RuntimeError("broadcaster died")

        with caplog.at_level(logging.ERROR):
            await self._settle(app_lifecycle._supervise("ws-broadcast", boom()))

        assert any(
            "ws-broadcast" in r.getMessage() and r.levelno >= logging.ERROR
            for r in caplog.records
        )

    async def test_unexpected_normal_exit_is_logged(self, caplog) -> None:
        async def returns_early() -> None:
            return None

        with caplog.at_level(logging.ERROR):
            await self._settle(
                app_lifecycle._supervise("ws-broadcast", returns_early())
            )

        assert any(
            "ws-broadcast" in r.getMessage() and r.levelno >= logging.ERROR
            for r in caplog.records
        )

    async def test_cancellation_is_silent(self, caplog) -> None:
        started = asyncio.Event()

        async def long_running() -> None:
            started.set()
            await asyncio.sleep(3600)

        task = app_lifecycle._supervise("ws-broadcast", long_running())
        await started.wait()
        with caplog.at_level(logging.ERROR):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)

        errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert errors == []
