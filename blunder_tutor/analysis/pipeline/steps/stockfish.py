from __future__ import annotations

from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.utils.chess_utils import score_to_cp

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext

MATE_SCORE_ANALYSIS = 100000


def _collect_positions(
    game: chess.pgn.Game,
) -> tuple[list[chess.Board], list[tuple[int, chess.Move, chess.Color, str]]]:
    board = game.board()
    positions = [board.copy()]
    move_metadata: list[tuple[int, chess.Move, chess.Color, str]] = []
    move_number = 1

    for move in game.mainline_moves():
        player = board.turn
        san = board.san(move)
        move_metadata.append((move_number, move, player, san))
        board.push(move)
        positions.append(board.copy())
        if board.turn == chess.WHITE:
            move_number += 1

    return positions, move_metadata


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

        engine = ctx.engine
        owns_engine = engine is None
        if owns_engine:
            _, engine = await chess.engine.popen_uci(ctx.engine_path)

        info_flags = chess.engine.INFO_SCORE | chess.engine.INFO_PV
        game_id = ctx.game_id

        try:
            positions, move_metadata = _collect_positions(ctx.game)

            infos: list[chess.engine.InfoDict | None] = []
            for pos in positions:
                if pos.is_checkmate():
                    infos.append(None)
                else:
                    infos.append(
                        await engine.analyse(pos, limit, game=game_id, info=info_flags)
                    )

            move_evals: list[dict] = []
            for i, (move_number, move, player, san) in enumerate(move_metadata):
                board = positions[i]
                info_before = infos[i]
                assert info_before is not None

                eval_before = score_to_cp(info_before["score"], player)
                ply = (board.fullmove_number - 1) * 2 + (
                    1 if player == chess.WHITE else 2
                )

                pv = info_before.get("pv", [])
                best_move_uci = None
                best_move_san = None
                best_line: list[str] = []
                best_move_eval = None

                if pv:
                    best_move_uci = pv[0].uci()
                    best_move_san = board.san(pv[0])

                    temp_board = board.copy()
                    for pv_move in pv[:5]:
                        best_line.append(temp_board.san(pv_move))
                        temp_board.push(pv_move)

                    best_move_eval = eval_before

                board_after = positions[i + 1]
                if board_after.is_checkmate():
                    eval_after = MATE_SCORE_ANALYSIS
                else:
                    info_after = infos[i + 1]
                    assert info_after is not None
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
