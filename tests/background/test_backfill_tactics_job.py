from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from blunder_tutor.background.jobs.backfill_tactics import BackfillTacticsJob
from blunder_tutor.constants import JOB_STATUS_COMPLETED, JOB_TYPE_BACKFILL_TACTICS
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.services.job_service import JobService


async def test_job_row_reaches_completed(job_repo: JobRepository):
    job_service = JobService(job_repository=job_repo, event_bus=EventBus(), scope="u")
    job_id = await job_service.create_job(JOB_TYPE_BACKFILL_TACTICS)
    analysis_repo = MagicMock()
    analysis_repo.get_game_ids_missing_tactics = AsyncMock(return_value=["g1"])
    analysis_repo.fetch_blunders_for_tactics_backfill = AsyncMock(return_value=[])

    result = await BackfillTacticsJob(job_service, analysis_repo, MagicMock()).execute(
        job_id
    )

    assert result == {"games_processed": 1, "blunders_classified": 0}
    assert (await job_repo.get_job(job_id))["status"] == JOB_STATUS_COMPLETED
