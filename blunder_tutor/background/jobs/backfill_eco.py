from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.analysis.pipeline.executor import PipelineExecutor
from blunder_tutor.analysis.pipeline.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback

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
        force = kwargs.get("force", False)
        game_ids = await self._select_game_ids(force)

        if not game_ids:
            empty = {"games_processed": 0, "games_classified": 0}
            await self.job_service.complete_job(job_id, empty)
            return empty

        return await self.job_service.run_with_lifecycle(
            job_id,
            len(game_ids),
            lambda progress: self._backfill(job_id, game_ids, force, progress),
        )

    async def _select_game_ids(self, force: bool) -> list[str]:
        if force:
            return await self.analysis_repo.get_all_analyzed_game_ids()
        return await self.analysis_repo.get_game_ids_missing_eco()

    async def _backfill(
        self,
        job_id: str,
        game_ids: list[str],
        force: bool,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        config = PipelineConfig.from_preset(
            PipelinePreset.BACKFILL_ECO,
            force_rerun=force,
        )
        pipeline = AnalysisPipeline(config, get_all_steps())
        games_processed = 0
        games_classified = 0

        for i, game_id in enumerate(game_ids):
            if await self._is_cancelled(job_id):
                break
            report = await self._executor.execute_pipeline(pipeline, game_id)
            if report.success and "eco" in report.steps_executed:
                games_classified += 1
            games_processed += 1
            await progress(i + 1)

        return {
            "games_processed": games_processed,
            "games_classified": games_classified,
        }

    async def _is_cancelled(self, job_id: str) -> bool:
        job = await self.job_service.get_job(job_id)
        return bool(job and job.get("status") == "failed")
