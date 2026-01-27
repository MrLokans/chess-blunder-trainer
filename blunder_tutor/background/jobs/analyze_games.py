"""Analyze games job implementation.

This module contains the AnalyzeGamesJob class which analyzes games
using a chess engine.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


def _find_engine_path() -> str:
    env_path = os.environ.get("STOCKFISH_BINARY")
    if env_path and Path(env_path).exists():
        return env_path

    for path in [
        "/usr/games/stockfish",
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
        "stockfish",
    ]:
        if Path(path).exists():
            return path

    which_path = shutil.which("stockfish")
    if which_path:
        return which_path

    raise FileNotFoundError("Stockfish engine not found")


@register_job
class AnalyzeGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "analyze"

    def __init__(
        self,
        job_service: JobService,
        game_repo: GameRepository,
        analysis_repo: AnalysisRepository,
    ) -> None:
        self.job_service = job_service
        self.game_repo = game_repo
        self.analysis_repo = analysis_repo

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        game_ids = kwargs.get("game_ids")
        source = kwargs.get("source")
        username = kwargs.get("username")

        if game_ids is None:
            game_ids = self.game_repo.list_unanalyzed_game_ids(source, username)

        if not game_ids:
            self.job_service.complete_job(job_id, {"analyzed": 0, "skipped": 0})
            return {"analyzed": 0, "skipped": 0}

        return await self._analyze_games(job_id, game_ids)

    async def _analyze_games(self, job_id: str, game_ids: list[str]) -> dict[str, Any]:
        from blunder_tutor.analysis.logic import GameAnalyzer

        self.job_service.update_job_status(job_id, "running")
        self.job_service.update_job_progress(job_id, 0, len(game_ids))

        engine_path = _find_engine_path()
        analyzer = GameAnalyzer(
            analysis_repo=self.analysis_repo,
            games_repo=self.game_repo,
            engine_path=engine_path,
        )

        analyzed = 0
        skipped = 0
        loop = asyncio.get_event_loop()

        try:
            for i, game_id in enumerate(game_ids):
                job = self.job_service.get_job(job_id)
                if job and job.get("status") == "failed":
                    return {"analyzed": analyzed, "skipped": skipped}

                if self.analysis_repo.analysis_exists(game_id):
                    skipped += 1
                    self.job_service.update_job_progress(job_id, i + 1, len(game_ids))
                    continue

                await loop.run_in_executor(None, analyzer.analyze_game, game_id)

                await loop.run_in_executor(
                    None, self.game_repo.mark_game_analyzed, game_id
                )

                analyzed += 1
                self.job_service.update_job_progress(job_id, i + 1, len(game_ids))

            result = {"analyzed": analyzed, "skipped": skipped}
            self.job_service.complete_job(job_id, result)
            return result

        except Exception as e:
            logger.error(f"Error in analysis job {job_id}: {e}")
            self.job_service.update_job_status(job_id, "failed", str(e))
            raise
