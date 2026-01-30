from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.analysis.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelineExecutor,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class BackfillECOJob(BaseJob):
    job_identifier: ClassVar[str] = "backfill_eco"

    def __init__(
        self,
        job_service: JobService,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
        engine_path: str,
    ) -> None:
        self.job_service = job_service
        self.analysis_repo = analysis_repo
        self.game_repo = game_repo
        self._executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path=engine_path,
        )

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        game_ids = await self.analysis_repo.get_game_ids_missing_eco()

        if not game_ids:
            result = {"games_processed": 0, "games_classified": 0}
            await self.job_service.complete_job(job_id, result)
            return result

        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, len(game_ids))

        games_processed = 0
        games_classified = 0
        available_steps = get_all_steps()

        try:
            config = PipelineConfig.from_preset(PipelinePreset.BACKFILL_ECO)
            pipeline = AnalysisPipeline(config, available_steps)

            for i, game_id in enumerate(game_ids):
                job = await self.job_service.get_job(job_id)
                if job and job.get("status") == "failed":
                    return {
                        "games_processed": games_processed,
                        "games_classified": games_classified,
                    }

                report = await self._executor.execute_pipeline(pipeline, game_id)
                if report.success and "eco" in report.steps_executed:
                    games_classified += 1
                games_processed += 1

                await self.job_service.update_job_progress(job_id, i + 1, len(game_ids))

            result = {
                "games_processed": games_processed,
                "games_classified": games_classified,
            }
            await self.job_service.complete_job(job_id, result)
            return result

        except Exception as e:
            logger.error(f"Error in backfill ECO job {job_id}: {e}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise
