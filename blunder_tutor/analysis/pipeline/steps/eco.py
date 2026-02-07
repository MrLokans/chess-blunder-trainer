from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from blunder_tutor.analysis.eco import classify_opening
from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext

logger = logging.getLogger(__name__)


class ECOClassifyStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "eco"

    async def execute(self, ctx: StepContext) -> StepResult:
        board = ctx.game.board()
        for move in ctx.game.mainline_moves():
            board.push(move)

        eco_code = None
        eco_name = None
        try:
            eco = classify_opening(board)
            if eco:
                eco_code = eco.code
                eco_name = eco.name
        except Exception:
            logger.debug(
                "ECO classification failed for %s, skipping", ctx.game_id, exc_info=True
            )

        await ctx.analysis_repo.update_game_eco(ctx.game_id, eco_code, eco_name)

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"eco_code": eco_code, "eco_name": eco_name},
        )
