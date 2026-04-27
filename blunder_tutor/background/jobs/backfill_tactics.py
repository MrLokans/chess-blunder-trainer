"""Background job for backfilling tactical patterns on existing blunders."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

import chess
import chess.pgn

from blunder_tutor.analysis.tactics import classify_blunder_tactics
from blunder_tutor.background.base import BaseJob
from blunder_tutor.events.event_types import JobEvent

if TYPE_CHECKING:
    from blunder_tutor.events.event_bus import EventBus
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


class BackfillTacticsJob(BaseJob):
    job_identifier = "backfill_tactics"

    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
        event_bus: EventBus,
    ):
        self.analysis_repo = analysis_repo
        self.game_repo = game_repo
        self.event_bus = event_bus
        self._log = logging.getLogger("BackfillTacticsJob")

    async def execute(self, job_id: str, **kwargs) -> dict:
        game_ids = await self.analysis_repo.get_game_ids_missing_tactics()
        total = len(game_ids)
        processed = 0
        blunders_classified = 0

        self._log.info("Backfilling tactics for %d games", total)

        for game_id in game_ids:
            try:
                count = await self._process_game(game_id)
                blunders_classified += count
            except Exception as e:
                self._log.warning("Failed to process game %s: %s", game_id, e)

            processed += 1

            if processed % 10 == 0 or processed == total:
                event = JobEvent.create_progress_updated(
                    job_id=job_id,
                    job_type=self.job_identifier,
                    current=processed,
                    total=total,
                )
                await self.event_bus.publish(event)

        return {
            "games_processed": processed,
            "blunders_classified": blunders_classified,
        }

    async def _process_game(self, game_id: str) -> int:
        """Process a single game and return number of blunders classified."""
        blunders = await self.analysis_repo.fetch_blunders_for_tactics_backfill(game_id)
        if not blunders:
            return 0

        game = await self.game_repo.load_game(game_id)
        if not game:
            return 0

        ply_to_board = _build_ply_to_board(game)
        updates = [
            update
            for blunder_data in blunders
            if (update := _classify_blunder(blunder_data, ply_to_board, game_id))
        ]

        if updates:
            await self.analysis_repo.update_moves_tactics_batch(updates)
        return len(updates)


def _build_ply_to_board(
    game: chess.pgn.Game,
) -> dict[int, tuple[chess.Board, chess.Move]]:
    board = game.board()
    ply_to_board: dict[int, tuple[chess.Board, chess.Move]] = {}
    for current_ply, move in enumerate(game.mainline_moves(), start=1):
        ply_to_board[current_ply] = (board.copy(), move)
        board.push(move)
    return ply_to_board


def _classify_blunder(
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
