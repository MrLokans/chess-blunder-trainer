from __future__ import annotations

import logging
from typing import Any, ClassVar

import chess.engine

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)

_CLASSIFICATION_BLUNDER = 3
_CLASSIFICATION_MISTAKE = 2
_CLASSIFICATION_INACCURACY = 1


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

        owns_coordinator = self._coordinator is None
        coordinator = self._coordinator or WorkCoordinator(self.analyzer.engine_path, 1)
        if owns_coordinator:
            await coordinator.start()

        try:  # noqa: WPS501 — own/borrowed coordinator pattern: shutdown is unconditional cleanup, not error handling.
            return await self.job_service.run_with_lifecycle(
                job_id,
                1,
                lambda progress: self._import(game_id, username, coordinator, progress),
            )
        finally:
            if owns_coordinator:
                await coordinator.shutdown()

    async def _import(  # noqa: WPS217 — drain + 3 metadata reads + progress are the inherent steps of single-PGN import.
        self,
        game_id: str,
        username: str,
        coordinator: WorkCoordinator,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        async def run_analysis(engine: chess.engine.UciProtocol) -> None:  # noqa: WPS430 — `coordinator.submit` callable; captures `game_id` for the engine task.
            await self.analyzer.analyze_game(game_id=game_id, engine=engine)
            await self.game_repo.mark_game_analyzed(game_id)

        coordinator.submit(run_analysis)
        await coordinator.drain()

        eco = await self.analysis_repo.get_game_eco(game_id)
        moves = await self.analysis_repo.fetch_moves(game_id)
        user_side = _resolve_user_side(await self.game_repo.get_game(game_id), username)
        counts = _classify_moves(moves, user_side)

        await progress(1)
        return {
            "game_id": game_id,
            "eco_code": eco.get("eco_code"),
            "eco_name": eco.get("eco_name"),
            **counts,
        }


def _resolve_user_side(game_meta: dict[str, Any] | None, username: str) -> int | None:
    if not game_meta or not username:
        return None
    uname_lower = username.lower()
    if (game_meta.get("white") or "").lower() == uname_lower:
        return 0
    if (game_meta.get("black") or "").lower() == uname_lower:
        return 1
    return None


def _classify_moves(
    moves: list[dict[str, Any]],
    user_side: int | None,
) -> dict[str, int]:
    user_moves = (
        [m for m in moves if m["player"] == user_side]
        if user_side is not None
        else moves
    )
    return {
        "total_moves": len(user_moves),
        "blunders": sum(
            1 for m in user_moves if m["classification"] == _CLASSIFICATION_BLUNDER
        ),
        "mistakes": sum(
            1 for m in user_moves if m["classification"] == _CLASSIFICATION_MISTAKE
        ),
        "inaccuracies": sum(
            1 for m in user_moves if m["classification"] == _CLASSIFICATION_INACCURACY
        ),
    }
