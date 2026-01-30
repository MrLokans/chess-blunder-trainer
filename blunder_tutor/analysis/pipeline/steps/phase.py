from __future__ import annotations

from typing import TYPE_CHECKING

import chess

from blunder_tutor.analysis.phase import classify_phase
from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext


def _iter_moves_with_board(
    game: chess.pgn.Game,
) -> list[tuple[int, int, chess.Board]]:
    board = game.board()
    move_number = 1
    results = []
    for move in game.mainline_moves():
        ply = (board.fullmove_number - 1) * 2 + (1 if board.turn == chess.WHITE else 2)
        results.append((ply, move_number, board.copy(stack=False)))
        board.push(move)
        if board.turn == chess.WHITE:
            move_number += 1
    return results


class PhaseClassifyStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "phase"

    async def execute(self, ctx: StepContext) -> StepResult:
        phases: list[dict] = []

        for ply, move_number, board in _iter_moves_with_board(ctx.game):
            phase = classify_phase(board, move_number)
            phases.append({"ply": ply, "move_number": move_number, "phase": phase})

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"phases": phases},
        )
