from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blunder_tutor.analysis.engine_pool import EnginePool, WorkCoordinator


def _make_mock_engine(*, alive: bool = True) -> AsyncMock:
    engine = AsyncMock()
    engine.quit = AsyncMock()
    engine.configure = AsyncMock()
    engine.options = {
        "Threads": MagicMock(default=1, min=1, max=512),
        "Hash": MagicMock(default=16, min=1, max=33554432),
    }
    rc = asyncio.Future()
    if not alive:
        rc.set_result(0)
    engine.returncode = rc
    return engine


@pytest.fixture
def mock_popen_uci():
    with patch("blunder_tutor.analysis.engine_pool.chess.engine.popen_uci") as mock:
        engines = []

        async def create_engine(path):
            engine = _make_mock_engine()
            engines.append(engine)
            return (MagicMock(), engine)

        mock.side_effect = create_engine
        yield mock, engines


class TestEnginePool:
    async def test_start_spawns_correct_number(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 3)
        await pool.start()

        assert mock.call_count == 3
        assert len(engines) == 3

        await pool.shutdown()

    async def test_start_configures_threads_and_hash(self, mock_popen_uci):
        _, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 2, threads_per_engine=4, hash_mb=256)
        await pool.start()

        for engine in engines:
            engine.configure.assert_called_once_with({"Threads": 4, "Hash": 256})

        await pool.shutdown()

    async def test_submit_distributes_across_workers(self, mock_popen_uci):
        _, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 2)
        await pool.start()

        seen_engines: list[object] = []
        lock = asyncio.Lock()

        async def work(engine):
            async with lock:
                seen_engines.append(engine)
            await asyncio.sleep(0)

        for _ in range(4):
            pool.submit(work)

        await pool.drain()
        await pool.shutdown()

        assert len(seen_engines) == 4
        assert set(seen_engines) == set(engines)

    async def test_submit_returns_future_with_result(self, mock_popen_uci):
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()

        async def work(engine):
            return 42

        future = pool.submit(work)
        await pool.drain()

        assert future.result() == 42
        await pool.shutdown()

    async def test_submit_returns_future_with_exception(self, mock_popen_uci):
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()

        async def work(engine):
            raise ValueError("boom")

        future = pool.submit(work)
        await pool.drain()

        with pytest.raises(ValueError, match="boom"):
            future.result()
        await pool.shutdown()

    async def test_dead_engine_replaced_during_work(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()
        assert mock.call_count == 1

        engines[0].returncode.set_result(0)

        used_engines: list[object] = []

        async def work(engine):
            used_engines.append(engine)

        pool.submit(work)
        await pool.drain()

        assert mock.call_count == 2
        assert used_engines[0] is engines[1]
        await pool.shutdown()

    async def test_shutdown_quits_all_alive(self, mock_popen_uci):
        _, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 3)
        await pool.start()
        await pool.shutdown()

        for engine in engines:
            engine.quit.assert_called_once()

    async def test_shutdown_skips_dead_engines(self, mock_popen_uci):
        _, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 2)
        await pool.start()

        engines[0].returncode.set_result(0)
        await pool.shutdown()

        engines[0].quit.assert_not_called()
        engines[1].quit.assert_called_once()

    async def test_shutdown_tolerates_quit_errors(self, mock_popen_uci):
        _, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 2)
        await pool.start()

        engines[0].quit.side_effect = Exception("process already dead")
        await pool.shutdown()

        engines[1].quit.assert_called_once()

    async def test_sequential_jobs_reuse_engine(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()

        used_engines: list[object] = []

        async def work(engine):
            used_engines.append(engine)

        for _ in range(5):
            pool.submit(work)

        await pool.drain()
        await pool.shutdown()

        assert mock.call_count == 1
        assert all(e is engines[0] for e in used_engines)

    async def test_no_respawn_during_shutdown(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()
        assert mock.call_count == 1

        engines[0].returncode.set_result(0)

        spawn_count_before = mock.call_count
        await pool.shutdown()

        assert mock.call_count == spawn_count_before

    async def test_worker_exits_on_cancellation(self, mock_popen_uci):
        pool = EnginePool("/fake/stockfish", 1)
        await pool.start()

        stall = asyncio.Event()

        async def slow_work(engine):
            await stall.wait()

        future = pool.submit(slow_work)
        await asyncio.sleep(0)

        for w in pool._workers:
            w.cancel()
        await asyncio.gather(*pool._workers, return_exceptions=True)

        assert future.cancelled()
        await pool.shutdown()

    async def test_task_timeout_kills_and_respawns_engine(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 1, task_timeout=0.05)
        await pool.start()
        assert mock.call_count == 1

        async def hang_forever(engine):
            await asyncio.sleep(999)

        future = pool.submit(hang_forever)
        await pool.drain()

        assert mock.call_count == 2
        with pytest.raises(TimeoutError):
            future.result()
        engines[0].kill.assert_called_once()
        await pool.shutdown()

    async def test_task_timeout_worker_continues_after_timeout(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        pool = EnginePool("/fake/stockfish", 1, task_timeout=0.05)
        await pool.start()

        async def hang(engine):
            await asyncio.sleep(999)

        async def fast(engine):
            return "ok"

        f1 = pool.submit(hang)
        f2 = pool.submit(fast)
        await pool.drain()

        with pytest.raises(TimeoutError):
            f1.result()
        assert f2.result() == "ok"
        await pool.shutdown()

    async def test_no_timeout_when_disabled(self, mock_popen_uci):
        pool = EnginePool("/fake/stockfish", 1, task_timeout=None)
        await pool.start()

        async def work(engine):
            return 42

        future = pool.submit(work)
        await pool.drain()
        assert future.result() == 42
        await pool.shutdown()


class TestWorkCoordinator:
    async def test_submit_and_drain(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        coord = WorkCoordinator("/fake/stockfish", pool_size=2)
        await coord.start()

        results: list[int] = []

        async def work(engine):
            results.append(1)

        for _ in range(4):
            coord.submit(work)
        await coord.drain()

        assert len(results) == 4
        assert mock.call_count == 2
        await coord.shutdown()

    async def test_submit_returns_awaitable_future(self, mock_popen_uci):
        coord = WorkCoordinator("/fake/stockfish", pool_size=1)
        await coord.start()

        async def work(engine):
            return "hello"

        future = coord.submit(work)
        result = await future

        assert result == "hello"
        await coord.shutdown()

    async def test_lifecycle(self, mock_popen_uci):
        mock, engines = mock_popen_uci
        coord = WorkCoordinator("/fake/stockfish", pool_size=2)
        await coord.start()
        assert mock.call_count == 2

        await coord.shutdown()
        for engine in engines:
            engine.quit.assert_called_once()
