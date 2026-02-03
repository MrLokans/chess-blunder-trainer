from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.utils.chess_utils import score_to_cp

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext


def _iter_moves(
    game: chess.pgn.Game,
) -> Iterable[tuple[int, chess.Move, chess.Board]]:
    board = game.board()
    move_number = 1
    for move in game.mainline_moves():
        board_before = board.copy(stack=False)
        yield move_number, move, board_before
        board.push(move)
        if board.turn == chess.WHITE:
            move_number += 1


class StockfishAnalysisStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "stockfish"

    async def execute(self, ctx: StepContext) -> StepResult:
        limit = (
            chess.engine.Limit(depth=ctx.depth)
            if ctx.time_limit is None
            else chess.engine.Limit(time=ctx.time_limit)
        )

        move_evals: list[dict] = []

        engine = ctx.engine
        owns_engine = engine is None
        if owns_engine:
            _, engine = await chess.engine.popen_uci(ctx.engine_path)

        try:
            for move_number, move, board in _iter_moves(ctx.game):
                player = board.turn
                info_before = await engine.analyse(board, limit)
                eval_before = score_to_cp(info_before["score"], player)
                san = board.san(move)
                ply = (board.fullmove_number - 1) * 2 + (
                    1 if player == chess.WHITE else 2
                )

                pv = info_before.get("pv", [])
                best_move_uci = None
                best_move_san = None
                best_line = []
                best_move_eval = None

                if pv:
                    best_move_uci = pv[0].uci()
                    best_move_san = board.san(pv[0])

                    temp_board = board.copy()
                    for pv_move in pv[:5]:
                        best_line.append(temp_board.san(pv_move))
                        temp_board.push(pv_move)

                    best_move_board = board.copy()
                    best_move_board.push(pv[0])
                    info_best = await engine.analyse(best_move_board, limit)
                    best_move_eval = score_to_cp(info_best["score"], player)

                board_after = board.copy(stack=False)
                board_after.push(move)

                if board_after.is_checkmate():
                    eval_after = 100000  # MATE_SCORE_ANALYSIS
                else:
                    info_after = await engine.analyse(board_after, limit)
                    eval_after = score_to_cp(info_after["score"], player)

                move_evals.append(
                    {
                        "ply": ply,
                        "move_number": move_number,
                        "player": "white" if player == chess.WHITE else "black",
                        "uci": move.uci(),
                        "san": san,
                        "eval_before": eval_before,
                        "eval_after": eval_after,
                        "info_before": info_before,
                        "best_move_uci": best_move_uci,
                        "best_move_san": best_move_san,
                        "best_line": " ".join(best_line) if best_line else None,
                        "best_move_eval": best_move_eval,
                        "board": board,
                    }
                )
        finally:
            if owns_engine:
                await engine.quit()

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"move_evals": move_evals},
        )
