from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import chess

from blunder_tutor.analysis.traps import get_trap_database

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.trap_repository import TrapRepository


def _resolve_user_color(game_info: dict) -> chess.Color | None:
    username = str(game_info.get("username", "")).lower()
    if not username:
        return None
    if str(game_info.get("white", "")).lower() == username:
        return chess.WHITE
    if str(game_info.get("black", "")).lower() == username:
        return chess.BLACK
    return None


def _replay_to_final(game) -> chess.Board:
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board


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
        game_info = await self.game_repo.get_game(game_id)
        if not game_info:
            return 0
        user_color = _resolve_user_color(game_info)
        if user_color is None:
            return 0

        game = await self.game_repo.load_game(game_id)
        trap_db = get_trap_database()
        matches = trap_db.match_game(_replay_to_final(game), user_color)

        for match in matches:
            await self._save_match(game_id, match, trap_db)

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

    async def _save_match(self, game_id: str, match, trap_db) -> None:
        trap_def = trap_db.get_trap(match.trap_id)
        victim_side = trap_def.victim_side if trap_def else "unknown"
        await self.trap_repo.save_trap_match(
            game_id=game_id,
            trap_id=match.trap_id,
            match_type=match.match_type,
            victim_side=victim_side,
            user_was_victim=match.user_was_victim,
            mistake_ply=match.mistake_ply,
        )
