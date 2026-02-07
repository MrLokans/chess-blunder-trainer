from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    get_context,
    set_context,
)


def _make_context(label: str) -> DependencyContext:
    return DependencyContext(
        db_path=Path(f"/fake/{label}.db"),
        event_bus=MagicMock(),
        engine_path=f"/fake/{label}",
    )


class TestDependencyContextIsolation:
    async def test_no_context_raises(self):
        clear_context()
        with pytest.raises(RuntimeError, match="not initialized"):
            get_context()

    async def test_set_and_get(self):
        ctx = _make_context("a")
        set_context(ctx)
        assert get_context() is ctx
        clear_context()

    async def test_concurrent_tasks_see_own_context(self):
        barrier = asyncio.Barrier(2)
        results: dict[str, str] = {}

        async def task(label: str):
            ctx = _make_context(label)
            set_context(ctx)
            await barrier.wait()
            await asyncio.sleep(0)
            observed = get_context()
            results[label] = observed.engine_path
            clear_context()

        await asyncio.gather(task("task_a"), task("task_b"))

        assert results["task_a"] == "/fake/task_a"
        assert results["task_b"] == "/fake/task_b"

    async def test_clear_does_not_affect_other_tasks(self):
        ready = asyncio.Event()

        async def setter():
            set_context(_make_context("setter"))
            ready.set()
            await asyncio.sleep(0.05)
            assert get_context().engine_path == "/fake/setter"

        async def clearer():
            await ready.wait()
            set_context(_make_context("clearer"))
            clear_context()
            with pytest.raises(RuntimeError):
                get_context()

        await asyncio.gather(setter(), clearer())
