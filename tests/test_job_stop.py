from __future__ import annotations

from unittest.mock import AsyncMock

from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_TYPE_ANALYZE,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.services.job_service import JobService


def _service(job_repo: JobRepository) -> JobService:
    return JobService(job_repository=job_repo, event_bus=EventBus(), scope="u")


async def test_stop_while_running_is_not_overwritten_by_completion(
    job_repo: JobRepository,
):
    service = _service(job_repo)
    job_id = await service.create_job(JOB_TYPE_ANALYZE)

    async def body(_progress):
        await service.update_job_status(job_id, JOB_STATUS_FAILED, "Cancelled by user")
        return {"analyzed": 1}

    await service.run_with_lifecycle(job_id, 1, body)

    job = await job_repo.get_job(job_id)
    assert job["status"] == JOB_STATUS_FAILED
    assert job["error_message"] == "Cancelled by user"


async def test_stop_while_pending_skips_body(job_repo: JobRepository):
    service = _service(job_repo)
    job_id = await service.create_job(JOB_TYPE_ANALYZE)
    await service.update_job_status(job_id, JOB_STATUS_FAILED, "Cancelled by user")
    body = AsyncMock(return_value={})

    await service.run_with_lifecycle(job_id, 1, body)

    body.assert_not_awaited()
    assert (await job_repo.get_job(job_id))["status"] == JOB_STATUS_FAILED


async def test_normal_run_completes(job_repo: JobRepository):
    service = _service(job_repo)
    job_id = await service.create_job(JOB_TYPE_ANALYZE)

    await service.run_with_lifecycle(job_id, 1, AsyncMock(return_value={"ok": 1}))

    assert (await job_repo.get_job(job_id))["status"] == JOB_STATUS_COMPLETED
