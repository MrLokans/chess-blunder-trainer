from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob


async def test_engine_failure_counts_as_failed_and_ticks_progress():
    job = AnalyzeGamesJob(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    coordinator = MagicMock()
    coordinator.run_all = AsyncMock(return_value=[None, TimeoutError("engine")])
    progress = AsyncMock()

    results = await job._submit_all(
        ["g1", "g2"], None, coordinator, asyncio.Event(), progress
    )

    assert results["failed"] == 1
    progress.assert_awaited_once_with(1)
