from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import chess

from blunder_tutor.analysis.traps import get_trap_database

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.trap_repository import TrapRepository


class TrapBackfillService:
    def __init__(
        self,
        game_repo: GameRepository,
        trap_repo: TrapRepository,
    ) -> None:
        self.game_repo = game_repo
        self.trap_repo = trap_repo

    async def get_games_needing_backfill(self) -> list[str]:
        return await self.trap_repo.get_analyzed_game_ids_without_trap_data()

    async def backfill_game(self, game_id: str) -> int:
        trap_db = get_trap_database()
        game = await self.game_repo.load_game(game_id)
        game_info = await self.game_repo.get_game(game_id)

        if not game_info:
            return 0

        username = game_info.get("username", "")
        white = game_info.get("white", "")
        black = game_info.get("black", "")

        if username and white and str(white).lower() == str(username).lower():
            user_color = chess.WHITE
        elif username and black and str(black).lower() == str(username).lower():
            user_color = chess.BLACK
        else:
            return 0

        board = game.board()
        for move in game.mainline_moves():
            board.push(move)

        matches = trap_db.match_game(board, user_color)

        for m in matches:
            trap_def = trap_db.get_trap(m.trap_id)
            victim_side = trap_def.victim_side if trap_def else "unknown"
            await self.trap_repo.save_trap_match(
                game_id=game_id,
                trap_id=m.trap_id,
                match_type=m.match_type,
                victim_side=victim_side,
                user_was_victim=m.user_was_victim,
                mistake_ply=m.mistake_ply,
            )

        return len(matches)

    async def backfill_all(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, int]:
        game_ids = await self.get_games_needing_backfill()
        total = len(game_ids)
        matched = 0

        for i, game_id in enumerate(game_ids):
            count = await self.backfill_game(game_id)
            if count > 0:
                matched += 1
            if progress_callback:
                progress_callback(i + 1, total)

        return {"games_processed": total, "games_with_traps": matched}
