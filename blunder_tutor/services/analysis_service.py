from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.constants import MATE_SCORE_WEB
from blunder_tutor.utils.chess_utils import board_from_fen, format_eval

if TYPE_CHECKING:
    from blunder_tutor.analysis.engine_pool import WorkCoordinator


@dataclass
class PositionAnalysis:
    eval_cp: int
    eval_display: str
    best_move_uci: str | None
    best_move_san: str | None
    best_line: list[str]


@dataclass
class MoveEvaluation:
    eval_cp: int
    eval_display: str


def _extract_best_line(
    board: chess.Board, pv: list[chess.Move]
) -> tuple[str | None, str | None, list[str]]:
    if not pv:
        return None, None, []
    best_uci = pv[0].uci()
    best_san = board.san(pv[0])
    line: list[str] = []
    temp_board = board.copy()
    for move in pv[:5]:
        line.append(temp_board.san(move))
        temp_board.push(move)
    return best_uci, best_san, line


def _eval_cp_from_info(info: chess.engine.InfoDict) -> int:
    score = info.get("score")
    return score.white().score(mate_score=MATE_SCORE_WEB) if score else 0


def _format_eval(eval_cp: int, player_color: str | None) -> str:
    if player_color:
        return format_eval(eval_cp, player_color)
    return str(eval_cp)


class AnalysisService:
    def __init__(self, coordinator: WorkCoordinator, limit: chess.engine.Limit) -> None:
        self._coordinator = coordinator
        self.limit = limit

    async def analyze_position(
        self, fen: str, player_color: str | None = None
    ) -> PositionAnalysis:
        board = chess.Board(fen)
        info = await self._analyse(board)
        eval_cp = _eval_cp_from_info(info)
        best_uci, best_san, best_line = _extract_best_line(board, info.get("pv", []))

        return PositionAnalysis(
            eval_cp=eval_cp,
            eval_display=_format_eval(eval_cp, player_color),
            best_move_uci=best_uci,
            best_move_san=best_san,
            best_line=best_line,
        )

    async def evaluate_move(
        self, fen: str, move_uci: str, player_color: str | None = None
    ) -> MoveEvaluation:
        board = board_from_fen(fen)

        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {move_uci}") from exc

        if move not in board.legal_moves:
            raise ValueError(f"Illegal move: {move_uci}")

        board.push(move)
        info = await self._analyse(board)
        eval_cp = _eval_cp_from_info(info)

        return MoveEvaluation(
            eval_cp=eval_cp,
            eval_display=_format_eval(eval_cp, player_color),
        )

    def get_move_san(self, fen: str, move_uci: str) -> str:
        board = board_from_fen(fen)
        try:
            move = chess.Move.from_uci(move_uci)
            return board.san(move)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {move_uci}") from exc

    async def _analyse(self, board: chess.Board) -> chess.engine.InfoDict:
        limit = self.limit

        async def _work(engine: chess.engine.UciProtocol) -> chess.engine.InfoDict:  # noqa: WPS430 — `coordinator.submit` closure; captures `board`/`limit`.
            return await engine.analyse(board, limit)

        return await self._coordinator.submit(_work)
