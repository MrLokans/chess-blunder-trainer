from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from blunder_tutor.analysis.phase import classify_phase
from blunder_tutor.utils.pgn_utils import board_before_ply

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


class PhaseBackfillService:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.game_repo = game_repo

    async def get_games_needing_backfill(self) -> list[str]:
        return await self.analysis_repo.get_game_ids_missing_phase()

    async def backfill_game(self, game_id: str) -> int:
        game = await self.game_repo.load_game(game_id)
        moves = await self.analysis_repo.fetch_moves_for_phase_backfill(game_id)

        if not moves:
            return 0

        updates: list[tuple[int, str, int]] = []
        for move_data in moves:
            ply = move_data["ply"]
            move_number = move_data["move_number"]
            board = board_before_ply(game, ply)
            phase = classify_phase(board, move_number)
            updates.append((phase, game_id, ply))

        if updates:
            await self.analysis_repo.update_moves_phases_batch(updates)

        return len(updates)

    async def backfill_all(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, int]:
        game_ids = await self.get_games_needing_backfill()
        total_games = len(game_ids)
        total_moves = 0

        for i, game_id in enumerate(game_ids):
            moves_updated = await self.backfill_game(game_id)
            total_moves += moves_updated

            if progress_callback:
                progress_callback(i + 1, total_games)

        return {"games_processed": total_games, "moves_updated": total_moves}
