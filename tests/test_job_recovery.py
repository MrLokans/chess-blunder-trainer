from __future__ import annotations

import asyncio

from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_RUNNING,
    JOB_TYPE_SYNC,
)
from blunder_tutor.repositories.job_repository import JobRepository
from tests.helpers.engine import make_test_client


async def _seed(db_path) -> tuple[str, str, str]:
    repo = JobRepository(db_path)
    running = await repo.create_job(JOB_TYPE_SYNC)
    await repo.update_job_status(running, JOB_STATUS_RUNNING)
    pending = await repo.create_job(JOB_TYPE_SYNC)
    done = await repo.create_job(JOB_TYPE_SYNC)
    await repo.complete_job(done, {})
    await repo.close()
    return running, pending, done


async def _statuses(db_path, *job_ids: str) -> list[tuple[str, object]]:
    repo = JobRepository(db_path)
    jobs = [await repo.get_job(job_id) for job_id in job_ids]
    await repo.close()
    return [(job["status"], job["error_message"]) for job in jobs]


def test_startup_fails_interrupted_jobs(test_config, db_path):
    running, pending, done = asyncio.run(_seed(db_path))

    list(make_test_client(test_config))  # boot and shut down the app

    statuses = asyncio.run(_statuses(db_path, running, pending, done))
    assert statuses == [
        (JOB_STATUS_FAILED, "interrupted"),
        (JOB_STATUS_FAILED, "interrupted"),
        (JOB_STATUS_COMPLETED, None),
    ]
