from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

import chess
import chess.pgn

from blunder_tutor.analysis.tactics import classify_blunder_tactics
from blunder_tutor.background.base import BaseJob

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback


class BackfillTacticsJob(BaseJob):
    job_identifier = "backfill_tactics"

    def __init__(
        self,
        job_service: JobService,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        self.job_service = job_service
        self.analysis_repo = analysis_repo
        self.game_repo = game_repo
        self._log = logging.getLogger("BackfillTacticsJob")

    async def execute(self, job_id: str, **kwargs) -> dict:
        game_ids = await self.analysis_repo.get_game_ids_missing_tactics()
        self._log.info("Backfilling tactics for %d games", len(game_ids))
        return await self.job_service.run_with_lifecycle(
            job_id,
            len(game_ids),
            lambda progress: self._backfill(game_ids, progress),
        )

    async def _backfill(
        self, game_ids: list[str], progress: ProgressCallback
    ) -> dict[str, Any]:
        blunders_classified = 0
        for processed, game_id in enumerate(game_ids, start=1):
            try:
                blunders_classified += await self._process_game(game_id)
            except Exception as e:
                self._log.warning("Failed to process game %s: %s", game_id, e)
            if processed % 10 == 0 or processed == len(game_ids):
                await progress(processed)

        return {
            "games_processed": len(game_ids),
            "blunders_classified": blunders_classified,
        }

    async def _process_game(self, game_id: str) -> int:
        blunders = await self.analysis_repo.fetch_blunders_for_tactics_backfill(game_id)
        if not blunders:
            return 0

        game = await self.game_repo.load_game(game_id)
        if not game:
            return 0

        ply_to_board = build_ply_to_board(game)
        updates = [
            update
            for blunder_data in blunders
            if (update := classify_blunder(blunder_data, ply_to_board, game_id))
        ]

        if updates:
            await self.analysis_repo.update_moves_tactics_batch(updates)
        return len(updates)


def build_ply_to_board(
    game: chess.pgn.Game,
) -> dict[int, tuple[chess.Board, chess.Move]]:
    board = game.board()
    ply_to_board: dict[int, tuple[chess.Board, chess.Move]] = {}
    for current_ply, move in enumerate(game.mainline_moves(), start=1):
        ply_to_board[current_ply] = (board.copy(), move)
        board.push(move)
    return ply_to_board


def classify_blunder(
    blunder_data: dict[str, Any],
    ply_to_board: dict[int, tuple[chess.Board, chess.Move]],
    game_id: str,
) -> tuple[int, str, str, int] | None:
    ply = blunder_data["ply"]
    if ply not in ply_to_board:
        return None
    board_before, actual_move = ply_to_board[ply]
    best_move = _parse_uci(blunder_data.get("best_move_uci"))
    result = classify_blunder_tactics(board_before, actual_move, best_move)
    return (result.primary_pattern.value, result.blunder_reason, game_id, ply)


def _parse_uci(uci: str | None) -> chess.Move | None:
    if not uci:
        return None
    with contextlib.suppress(ValueError):
        return chess.Move.from_uci(uci)
    return None
