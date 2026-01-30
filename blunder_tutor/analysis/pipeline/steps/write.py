from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext


class WriteAnalysisStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "write"

    @property
    def depends_on(self) -> frozenset[str]:
        return frozenset({"move_quality", "phase", "eco"})

    async def execute(self, ctx: StepContext) -> StepResult:
        move_quality_result = ctx.get_step_result("move_quality")
        phase_result = ctx.get_step_result("phase")
        eco_result = ctx.get_step_result("eco")

        if not move_quality_result or not move_quality_result.success:
            return StepResult(
                step_id=self.step_id,
                success=False,
                error="move_quality step not completed",
            )

        if not phase_result or not phase_result.success:
            return StepResult(
                step_id=self.step_id,
                success=False,
                error="phase step not completed",
            )

        moves = move_quality_result.data.get("moves", [])
        phases = {p["ply"]: p["phase"] for p in phase_result.data.get("phases", [])}

        for move in moves:
            move["game_phase"] = phases.get(move["ply"])

        eco_code = None
        eco_name = None
        if eco_result and eco_result.success:
            eco_code = eco_result.data.get("eco_code")
            eco_name = eco_result.data.get("eco_name")

        analyzed_at = datetime.now(UTC).isoformat()
        await ctx.analysis_repo.write_analysis(
            game_id=ctx.game_id,
            pgn_path="",
            analyzed_at=analyzed_at,
            engine_path=ctx.engine_path,
            depth=ctx.depth,
            time_limit=ctx.time_limit,
            thresholds={
                "inaccuracy": ctx.thresholds.inaccuracy,
                "mistake": ctx.thresholds.mistake,
                "blunder": ctx.thresholds.blunder,
            },
            moves=moves,
            eco_code=eco_code,
            eco_name=eco_name,
        )

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"moves_written": len(moves)},
        )
