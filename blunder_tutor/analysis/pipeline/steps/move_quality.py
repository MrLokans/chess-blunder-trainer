from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import chess.engine

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext
    from blunder_tutor.analysis.thresholds import Thresholds


def _is_mate_score(score: chess.engine.PovScore, side: chess.Color) -> bool:
    pov = score.pov(side)
    return pov.is_mate()


def _classify(delta: int, thresholds: Thresholds) -> str:
    if delta >= thresholds.blunder:
        return "blunder"
    if delta >= thresholds.mistake:
        return "mistake"
    if delta >= thresholds.inaccuracy:
        return "inaccuracy"
    return "good"


def _class_to_int(label: str) -> int:
    return {"good": 0, "inaccuracy": 1, "mistake": 2, "blunder": 3}[label]


class MoveQualityStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "move_quality"

    @property
    def depends_on(self) -> frozenset[str]:
        return frozenset({"stockfish"})

    async def execute(self, ctx: StepContext) -> StepResult:
        stockfish_result = ctx.get_step_result("stockfish")
        if not stockfish_result or not stockfish_result.success:
            return StepResult(
                step_id=self.step_id,
                success=False,
                error="Stockfish step not completed",
            )

        move_evals = stockfish_result.data.get("move_evals", [])
        thresholds = ctx.thresholds

        moves: list[dict] = []
        for move_data in move_evals:
            eval_before = move_data["eval_before"]
            eval_after = move_data["eval_after"]
            info_before = move_data["info_before"]
            player = chess.WHITE if move_data["player"] == "white" else chess.BLACK

            if eval_after == 100000:  # Checkmate
                delta = 0
                cp_loss = 0
                class_label = "good"
            else:
                delta = eval_before - eval_after
                cp_loss = max(0, delta)

                if _is_mate_score(info_before["score"], player) and eval_after > 500:
                    cp_loss = min(cp_loss, thresholds.inaccuracy - 1)

                class_label = _classify(cp_loss, thresholds)

            moves.append(
                {
                    "ply": move_data["ply"],
                    "move_number": move_data["move_number"],
                    "player": move_data["player"],
                    "uci": move_data["uci"],
                    "san": move_data["san"],
                    "eval_before": eval_before,
                    "eval_after": eval_after,
                    "delta": delta,
                    "cp_loss": cp_loss,
                    "classification": _class_to_int(class_label),
                    "best_move_uci": move_data["best_move_uci"],
                    "best_move_san": move_data["best_move_san"],
                    "best_line": move_data["best_line"],
                    "best_move_eval": move_data["best_move_eval"],
                }
            )

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"moves": moves, "analyzed_at": datetime.now(UTC).isoformat()},
        )
