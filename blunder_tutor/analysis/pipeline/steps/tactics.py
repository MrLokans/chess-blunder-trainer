"""Pipeline step for tactical pattern detection on blunders."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import chess

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.analysis.tactics import (
    PATTERN_LABELS,
    classify_blunder_tactics,
)

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext


class TacticsClassifyStep(AnalysisStep):
    """Detect tactical patterns in blunder positions.

    Analyzes each blunder to identify:
    - What tactical patterns the best move exploited (fork, pin, etc.)
    - What weaknesses the blunder created in the position
    """

    @property
    def step_id(self) -> str:
        return "tactics"

    @property
    def depends_on(self) -> frozenset[str]:
        return frozenset({"move_quality"})

    async def execute(self, ctx: StepContext) -> StepResult:
        move_quality_result = ctx.get_step_result("move_quality")
        if not move_quality_result or not move_quality_result.success:
            return StepResult(
                step_id=self.step_id,
                success=False,
                error="Move quality step not completed",
            )

        moves = move_quality_result.data.get("moves", [])
        tactics_data: list[dict] = []

        # Build board state for each move
        board = ctx.game.board()
        move_iter = iter(ctx.game.mainline_moves())

        for move_data in moves:
            ply = move_data["ply"]
            classification = move_data["classification"]

            # Get the actual move
            try:
                move = next(move_iter)
            except StopIteration:
                break

            board_before = board.copy()

            # Only analyze blunders (classification == 3)
            if classification == 3:  # Blunder
                best_move_uci = move_data.get("best_move_uci")
                best_move = None
                if best_move_uci:
                    with contextlib.suppress(ValueError):
                        best_move = chess.Move.from_uci(best_move_uci)

                # Analyze tactics around this blunder
                result = classify_blunder_tactics(board_before, move, best_move)

                tactics_data.append(
                    {
                        "ply": ply,
                        "primary_pattern": result.primary_pattern.value,
                        "primary_pattern_name": result.primary_pattern_name,
                        "blunder_reason": result.blunder_reason,
                        "missed_tactic": PATTERN_LABELS[result.missed_tactic.pattern]
                        if result.missed_tactic
                        else None,
                        "allowed_tactic": PATTERN_LABELS[result.allowed_tactic.pattern]
                        if result.allowed_tactic
                        else None,
                    }
                )

            # Advance the board
            board.push(move)

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"tactics": tactics_data},
        )
