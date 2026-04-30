from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import chess

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.analysis.traps import get_trap_database
from blunder_tutor.repositories.trap_repository import TrapRepository

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext

logger = logging.getLogger(__name__)


class TrapDetectionStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "traps"

    async def execute(self, ctx: StepContext) -> StepResult:
        trap_db = get_trap_database()

        board = ctx.game.board()
        for move in ctx.game.mainline_moves():
            board.push(move)

        game_info = await ctx.game_repo.get_game(ctx.game_id)
        if not game_info:
            return StepResult(
                step_id=self.step_id,
                success=True,
                data={"matches": [], "reason": "game_info_not_found"},
            )

        username = game_info.get("username", "")
        white = game_info.get("white", "")
        black = game_info.get("black", "")

        if username and white and str(white).lower() == str(username).lower():
            user_color = chess.WHITE
        elif username and black and str(black).lower() == str(username).lower():
            user_color = chess.BLACK
        else:
            return StepResult(
                step_id=self.step_id,
                success=True,
                data={"matches": [], "reason": "user_color_unknown"},
            )

        matches = trap_db.match_game(board, user_color)

        if matches:
            async with TrapRepository(db_path=ctx.analysis_repo.db_path) as trap_repo:
                for match in matches:
                    victim_side = (
                        trap_db.get_trap(match.trap_id).victim_side
                        if trap_db.get_trap(match.trap_id)
                        else "unknown"
                    )
                    await trap_repo.save_trap_match(
                        game_id=ctx.game_id,
                        trap_id=match.trap_id,
                        match_type=match.match_type,
                        victim_side=victim_side,
                        user_was_victim=match.user_was_victim,
                        mistake_ply=match.mistake_ply,
                    )

            logger.info(
                "Found %d trap matches for game %s: %s",
                len(matches),
                ctx.game_id,
                [m.trap_id for m in matches],
            )

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={
                "matches": [
                    {
                        "trap_id": m.trap_id,
                        "match_type": m.match_type,
                        "user_was_victim": m.user_was_victim,
                    }
                    for m in matches
                ]
            },
        )
