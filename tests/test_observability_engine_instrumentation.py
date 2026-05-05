"""Smoke test: Stockfish engine chokepoint emits the expected facade calls.

Wraps the real `EnginePool._handle_task` chokepoint with mock engines and
asserts the facade is called with the documented metric/span shape. Does
not exercise sentry_sdk semantics — Phase 1 already covers facade dispatch.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blunder_tutor.analysis import engine_pool
from blunder_tutor.analysis.engine_pool import EnginePool
from tests.helpers.observability import FacadeCallRecorder, patch_facade


def _make_mock_engine() -> AsyncMock:
    engine = AsyncMock()
    engine.quit = AsyncMock()
    engine.configure = AsyncMock()
    engine.kill = MagicMock()
    engine.options = {
        "Threads": MagicMock(default=1),
        "Hash": MagicMock(default=16),
    }
    engine.returncode = asyncio.Future()
    return engine


@pytest.fixture
def mock_popen_uci():
    with patch("blunder_tutor.analysis.engine_pool.chess.engine.popen_uci") as mock:

        async def create_engine(_path: str):
            return MagicMock(), _make_mock_engine()

        mock.side_effect = create_engine
        yield mock


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> FacadeCallRecorder:
    return patch_facade(monkeypatch, engine_pool)


class TestEngineInstrumentation:
    async def test_successful_task_emits_span_and_metrics(
        self, mock_popen_uci, recorder: FacadeCallRecorder
    ):
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()

        async def work(_engine):
            return "ok"

        future = pool.submit(work)
        result = await asyncio.wait_for(future, timeout=2.0)
        await pool.shutdown()

        assert result == "ok"
        assert recorder.spans == [{"name": "engine.analyse", "op": "chess.engine"}]
        assert recorder.counts == [
            {
                "name": "engine.analyse.completed",
                "value": 1.0,
                "tags": {"outcome": "ok"},
            }
        ]
        assert len(recorder.distributions) == 1
        duration = recorder.distributions[0]
        assert duration["name"] == "engine.analyse.duration_ms"
        assert duration["value"] >= 0

    async def test_failed_task_emits_error_outcome(
        self, mock_popen_uci, recorder: FacadeCallRecorder
    ):
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()

        async def boom(_engine):
            raise ValueError("boom")

        future = pool.submit(boom)
        with pytest.raises(ValueError, match="boom"):
            await asyncio.wait_for(future, timeout=2.0)
        await pool.shutdown()

        assert recorder.counts == [
            {
                "name": "engine.analyse.completed",
                "value": 1.0,
                "tags": {"outcome": "error"},
            }
        ]
        assert len(recorder.distributions) == 1
