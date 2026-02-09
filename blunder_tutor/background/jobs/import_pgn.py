from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    import chess.engine

    from blunder_tutor.analysis.engine_pool import WorkCoordinator
    from blunder_tutor.analysis.logic import GameAnalyzer
    from blunder_tutor.events.event_bus import EventBus
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class ImportPgnJob(BaseJob):
    job_identifier: ClassVar[str] = "import_pgn"

    def __init__(
        self,
        job_service: JobService,
        game_repo: GameRepository,
        analysis_repo: AnalysisRepository,
        analyzer: GameAnalyzer,
        event_bus: EventBus | None = None,
        coordinator: WorkCoordinator | None = None,
    ) -> None:
        self.job_service = job_service
        self.game_repo = game_repo
        self.analysis_repo = analysis_repo
        self.analyzer = analyzer
        self._event_bus = event_bus
        self._coordinator = coordinator

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        game_id: str = kwargs["game_id"]
        username: str = kwargs.get("username", "")

        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, 1)

        from blunder_tutor.analysis.engine_pool import WorkCoordinator

        owns_coordinator = self._coordinator is None
        coordinator = self._coordinator or WorkCoordinator(self.analyzer.engine_path, 1)
        if owns_coordinator:
            await coordinator.start()

        try:

            async def run_analysis(engine: chess.engine.UciProtocol) -> None:
                await self.analyzer.analyze_game(game_id=game_id, engine=engine)
                await self.game_repo.mark_game_analyzed(game_id)

            coordinator.submit(run_analysis)
            await coordinator.drain()

            eco = await self.analysis_repo.get_game_eco(game_id)
            moves = await self.analysis_repo.fetch_moves(game_id)

            game_meta = await self.game_repo.get_game(game_id)
            user_side: int | None = None
            if game_meta and username:
                uname_lower = username.lower()
                white = (game_meta.get("white") or "").lower()
                black = (game_meta.get("black") or "").lower()
                if white == uname_lower:
                    user_side = 0
                elif black == uname_lower:
                    user_side = 1

            if user_side is not None:
                user_moves = [m for m in moves if m["player"] == user_side]
            else:
                user_moves = moves

            total_moves = len(user_moves)
            blunders = sum(1 for m in user_moves if m["classification"] == 3)
            mistakes = sum(1 for m in user_moves if m["classification"] == 2)
            inaccuracies = sum(1 for m in user_moves if m["classification"] == 1)

            result = {
                "game_id": game_id,
                "eco_code": eco.get("eco_code"),
                "eco_name": eco.get("eco_name"),
                "total_moves": total_moves,
                "blunders": blunders,
                "mistakes": mistakes,
                "inaccuracies": inaccuracies,
            }

            await self.job_service.update_job_progress(job_id, 1, 1)
            await self.job_service.complete_job(job_id, result)
            return result

        except Exception as e:
            logger.error("Failed to analyze imported game %s: %s", game_id, e)
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise

        finally:
            if owns_coordinator:
                await coordinator.shutdown()
