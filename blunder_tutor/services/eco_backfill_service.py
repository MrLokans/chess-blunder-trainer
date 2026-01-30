from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from blunder_tutor.analysis.eco import classify_opening

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


class ECOBackfillService:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.game_repo = game_repo

    async def get_games_needing_backfill(self) -> list[str]:
        return await self.analysis_repo.get_game_ids_missing_eco()

    async def backfill_game(self, game_id: str) -> bool:
        game = await self.game_repo.load_game(game_id)

        board = game.board()
        for move in game.mainline_moves():
            board.push(move)

        eco = classify_opening(board)
        eco_code = eco.code if eco else None
        eco_name = eco.name if eco else None

        await self.analysis_repo.update_game_eco(game_id, eco_code, eco_name)
        return eco is not None

    async def backfill_all(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, int]:
        game_ids = await self.get_games_needing_backfill()
        total_games = len(game_ids)
        classified = 0

        for i, game_id in enumerate(game_ids):
            was_classified = await self.backfill_game(game_id)
            if was_classified:
                classified += 1

            if progress_callback:
                progress_callback(i + 1, total_games)

        return {"games_processed": total_games, "games_classified": classified}
