from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.utils.chess_utils import score_to_cp

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext

MATE_SCORE_ANALYSIS = 100000


@dataclass(frozen=True)
class MoveMetadata:
    move_number: int
    move: chess.Move
    player: chess.Color
    san: str


@dataclass(frozen=True)
class PositionWalk:
    positions: list[chess.Board]
    moves: list[MoveMetadata]


def _collect_positions(game: chess.pgn.Game) -> PositionWalk:
    board = game.board()
    positions = [board.copy()]
    moves: list[MoveMetadata] = []
    move_number = 1

    for move in game.mainline_moves():
        player = board.turn
        san = board.san(move)
        moves.append(MoveMetadata(move_number, move, player, san))
        board.push(move)
        positions.append(board.copy())
        if board.turn == chess.WHITE:
            move_number += 1

    return PositionWalk(positions=positions, moves=moves)


def _pv_summary(
    board: chess.Board,
    info: chess.engine.InfoDict,
    eval_before: int,
) -> dict:
    pv = info.get("pv", [])
    if not pv:
        return {
            "best_move_uci": None,
            "best_move_san": None,
            "best_line": None,
            "best_move_eval": None,
        }

    cursor = board.copy()
    line: list[str] = []
    for pv_move in pv[:5]:
        line.append(cursor.san(pv_move))
        cursor.push(pv_move)

    return {
        "best_move_uci": pv[0].uci(),
        "best_move_san": board.san(pv[0]),
        "best_line": " ".join(line),
        "best_move_eval": eval_before,
    }


def _eval_after(
    walk: PositionWalk,
    infos: list[chess.engine.InfoDict | None],
    idx: int,
    player: chess.Color,
) -> int:
    board_after = walk.positions[idx + 1]
    if board_after.is_checkmate():
        return MATE_SCORE_ANALYSIS
    info_after = infos[idx + 1]
    assert info_after is not None
    return score_to_cp(info_after["score"], player)


def _build_move_eval(
    walk: PositionWalk,
    infos: list[chess.engine.InfoDict | None],
    idx: int,
) -> dict:
    meta = walk.moves[idx]
    board = walk.positions[idx]
    info_before = infos[idx]
    assert info_before is not None
    eval_before = score_to_cp(info_before["score"], meta.player)
    ply = (board.fullmove_number - 1) * 2 + (
        1 if meta.player == chess.WHITE else 2  # noqa: WPS509 — single parenthesized ternary inside arithmetic, no nesting.
    )
    eval_after = _eval_after(walk, infos, idx, meta.player)

    return {
        "ply": ply,
        "move_number": meta.move_number,
        "player": "white" if meta.player == chess.WHITE else "black",
        "uci": meta.move.uci(),
        "san": meta.san,
        "eval_before": eval_before,
        "eval_after": eval_after,
        "info_before": info_before,
        "board": board,
        **_pv_summary(board, info_before, eval_before),
    }


async def _analyze_game(
    game: chess.pgn.Game,
    game_id: str,
    engine: chess.engine.UciProtocol,
    limit: chess.engine.Limit,
    info_flags: int,
) -> list[dict]:
    walk = _collect_positions(game)
    infos: list[chess.engine.InfoDict | None] = []
    for pos in walk.positions:
        if pos.is_checkmate():
            infos.append(None)
        else:
            infos.append(
                await engine.analyse(pos, limit, game=game_id, info=info_flags)
            )
    return [_build_move_eval(walk, infos, idx) for idx in range(len(walk.moves))]


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
        try:  # noqa: WPS501 — conditional cleanup (`if owns_engine: engine.quit()`); not a single-resource context manager.
            move_evals = await _analyze_game(
                ctx.game, ctx.game_id, engine, limit, info_flags
            )
        finally:
            if owns_engine:
                await engine.quit()

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"move_evals": move_evals},
        )
