from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.analysis.logic import GameAnalyzer
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class AnalyzeGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "analyze"

    def __init__(
        self,
        job_service: JobService,
        game_repo: GameRepository,
        analysis_repo: AnalysisRepository,
        analyzer: GameAnalyzer,
    ) -> None:
        self.job_service = job_service
        self.game_repo = game_repo
        self.analysis_repo = analysis_repo
        self.analyzer = analyzer

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        game_ids = kwargs.get("game_ids")
        source = kwargs.get("source")
        username = kwargs.get("username")
        steps = kwargs.get("steps")

        if game_ids is None:
            game_ids = await self.game_repo.list_unanalyzed_game_ids(source, username)

        if not game_ids:
            await self.job_service.complete_job(job_id, {"analyzed": 0, "skipped": 0})
            return {"analyzed": 0, "skipped": 0}

        return await self._analyze_games(job_id, game_ids, steps)

    async def _analyze_games(
        self, job_id: str, game_ids: list[str], steps: list[str] | None = None
    ) -> dict[str, Any]:
        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, len(game_ids))

        analyzed = 0
        skipped = 0

        try:
            for i, game_id in enumerate(game_ids):
                job = await self.job_service.get_job(job_id)
                if job and job.get("status") == "failed":
                    return {"analyzed": analyzed, "skipped": skipped}

                if await self.analysis_repo.analysis_exists(game_id):
                    skipped += 1
                    await self.job_service.update_job_progress(
                        job_id, i + 1, len(game_ids)
                    )
                    continue

                await self.analyzer.analyze_game(game_id, steps=steps)
                await self.game_repo.mark_game_analyzed(game_id)

                analyzed += 1
                await self.job_service.update_job_progress(job_id, i + 1, len(game_ids))

            result = {"analyzed": analyzed, "skipped": skipped}
            await self.job_service.complete_job(job_id, result)
            return result

        except Exception as e:
            logger.error(f"Error in analysis job {job_id}: {e}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise
