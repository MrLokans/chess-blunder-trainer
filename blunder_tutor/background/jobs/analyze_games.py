from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, ClassVar

import chess.engine

from blunder_tutor.analysis.logic import DEFAULT_CONCURRENCY
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
        concurrency = kwargs.get("concurrency", DEFAULT_CONCURRENCY)

        if game_ids is None:
            game_ids = await self.game_repo.list_unanalyzed_game_ids(source, username)

        if not game_ids:
            await self.job_service.complete_job(job_id, {"analyzed": 0, "skipped": 0})
            return {"analyzed": 0, "skipped": 0}

        return await self._analyze_games(job_id, game_ids, steps, concurrency)

    async def _analyze_games(
        self,
        job_id: str,
        game_ids: list[str],
        steps: list[str] | None = None,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> dict[str, Any]:
        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, len(game_ids))

        results = {"analyzed": 0, "skipped": 0, "failed": 0}
        processed = 0
        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def process_game(game_id: str) -> None:
            nonlocal processed

            job = await self.job_service.get_job(job_id)
            if job and job.get("status") == "failed":
                return

            async with semaphore:
                if await self.analysis_repo.analysis_exists(game_id):
                    async with lock:
                        results["skipped"] += 1
                        processed += 1
                        await self.job_service.update_job_progress(
                            job_id, processed, len(game_ids)
                        )
                    return

                engine = None
                try:
                    _, engine = await chess.engine.popen_uci(self.analyzer.engine_path)
                    await self.analyzer.analyze_game(
                        game_id, steps=steps, engine=engine
                    )
                    await self.game_repo.mark_game_analyzed(game_id)

                    async with lock:
                        results["analyzed"] += 1
                        processed += 1
                        await self.job_service.update_job_progress(
                            job_id, processed, len(game_ids)
                        )
                except Exception as e:
                    logger.error(f"Failed to analyze game {game_id}: {e}")
                    async with lock:
                        results["failed"] += 1
                        processed += 1
                        await self.job_service.update_job_progress(
                            job_id, processed, len(game_ids)
                        )
                finally:
                    if engine is not None:
                        await engine.quit()

        try:
            logger.info(
                f"Starting parallel analysis of {len(game_ids)} games "
                f"with concurrency={concurrency}"
            )
            tasks = [asyncio.create_task(process_game(gid)) for gid in game_ids]
            await asyncio.gather(*tasks)

            await self.job_service.complete_job(job_id, results)
            return results

        except asyncio.CancelledError:
            logger.info(f"Analysis job {job_id} cancelled, cleaning up...")
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        except Exception as e:
            logger.error(f"Error in analysis job {job_id}: {e}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise
