from __future__ import annotations

from typing import TYPE_CHECKING

from blunder_tutor.analysis.eco import classify_opening
from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext


class ECOClassifyStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "eco"

    async def execute(self, ctx: StepContext) -> StepResult:
        board = ctx.game.board()
        for move in ctx.game.mainline_moves():
            board.push(move)

        eco = classify_opening(board)
        eco_code = eco.code if eco else None
        eco_name = eco.name if eco else None

        await ctx.analysis_repo.update_game_eco(ctx.game_id, eco_code, eco_name)

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"eco_code": eco_code, "eco_name": eco_name},
        )

    async def is_completed(self, ctx: StepContext) -> bool:
        eco_data = await ctx.analysis_repo.get_game_eco(ctx.game_id)
        return eco_data.get("eco_code") is not None
