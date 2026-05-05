"""Smoke test: background job chokepoint emits a transaction-shaped span,
the bounded-cardinality counters, and a duration distribution.

Cardinality discipline check: `user_id` and `job_id` must travel as span
attributes (set_tag / set_data), never as metric tags. Verified explicitly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from blunder_tutor.background import executor as executor_module
from blunder_tutor.background.executor import JobExecutor
from tests.helpers.observability import FacadeCallRecorder, patch_facade

_TEST_JOB_KIND = "observability_smoke_test"


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> FacadeCallRecorder:
    return patch_facade(monkeypatch, executor_module)


def _install_runner(monkeypatch: pytest.MonkeyPatch, runner: AsyncMock) -> None:
    monkeypatch.setattr(executor_module, "JOB_RUNNERS", {_TEST_JOB_KIND: runner})


def _make_executor(db_path) -> JobExecutor:
    return JobExecutor(
        event_bus=MagicMock(),
        db_path_resolver=lambda _uid: db_path,
        engine_path="/fake/stockfish",
        work_coordinator=None,
    )


class TestJobInstrumentation:
    async def test_successful_job_emits_transaction_and_metrics(
        self, tmp_path, recorder: FacadeCallRecorder, monkeypatch: pytest.MonkeyPatch
    ):
        runner = AsyncMock(return_value="done")
        _install_runner(monkeypatch, runner)

        executor = _make_executor(tmp_path / "user.sqlite")
        await executor._execute_job(
            job_id="job-123",
            job_type=_TEST_JOB_KIND,
            user_id="user-1",
            kwargs={},
        )

        assert recorder.spans == [{"name": _TEST_JOB_KIND, "op": "job"}]
        assert ("user_id", "user-1") in recorder.tags
        assert ("job_id", "job-123") in recorder.data

        names = [c["name"] for c in recorder.counts]
        assert "job.started" in names
        assert "job.completed" in names

        completed = next(c for c in recorder.counts if c["name"] == "job.completed")
        assert completed["tags"] == {"kind": _TEST_JOB_KIND, "status": "ok"}

        assert len(recorder.distributions) == 1
        duration = recorder.distributions[0]
        assert duration["name"] == "job.duration_ms"
        assert duration["tags"] == {"kind": _TEST_JOB_KIND}

    async def test_failing_job_emits_error_status_and_reraises(
        self, tmp_path, recorder: FacadeCallRecorder, monkeypatch: pytest.MonkeyPatch
    ):
        runner = AsyncMock(side_effect=RuntimeError("boom"))
        _install_runner(monkeypatch, runner)
        executor = _make_executor(tmp_path / "user.sqlite")

        with pytest.raises(RuntimeError, match="boom"):
            await executor._execute_job(
                job_id="job-456",
                job_type=_TEST_JOB_KIND,
                user_id="user-2",
                kwargs={},
            )

        completed = [c for c in recorder.counts if c["name"] == "job.completed"]
        assert completed == [
            {
                "name": "job.completed",
                "value": 1.0,
                "tags": {"kind": _TEST_JOB_KIND, "status": "error"},
            }
        ]

    async def test_cancelled_job_records_error_status(
        self, tmp_path, recorder: FacadeCallRecorder, monkeypatch: pytest.MonkeyPatch
    ):
        """`asyncio.CancelledError` is BaseException, not Exception. The
        ``except BaseException`` widening in `_execute_job` is what flips
        status to "error" before the cancellation propagates — without it
        the metric would silently miscount cancellations as "ok".
        """
        import asyncio as _asyncio

        runner = AsyncMock(side_effect=_asyncio.CancelledError())
        _install_runner(monkeypatch, runner)
        executor = _make_executor(tmp_path / "user.sqlite")

        with pytest.raises(_asyncio.CancelledError):
            await executor._execute_job(
                job_id="job-789",
                job_type=_TEST_JOB_KIND,
                user_id="user-3",
                kwargs={},
            )

        completed = [c for c in recorder.counts if c["name"] == "job.completed"]
        assert completed == [
            {
                "name": "job.completed",
                "value": 1.0,
                "tags": {"kind": _TEST_JOB_KIND, "status": "error"},
            }
        ]

    async def test_metric_tags_never_carry_user_or_job_id(
        self, tmp_path, recorder: FacadeCallRecorder, monkeypatch: pytest.MonkeyPatch
    ):
        """Cardinality rule: IDs go on span attributes, never on metric tags."""
        runner = AsyncMock(return_value=None)
        _install_runner(monkeypatch, runner)
        executor = _make_executor(tmp_path / "user.sqlite")

        await executor._execute_job(
            job_id="abc-correlation",
            job_type=_TEST_JOB_KIND,
            user_id="user-with-id",
            kwargs={},
        )

        for record in recorder.counts + recorder.distributions:
            tag_keys = set((record["tags"] or {}).keys())
            assert "user_id" not in tag_keys
            assert "job_id" not in tag_keys
            assert tag_keys.issubset({"kind", "status"})
