from __future__ import annotations

from dataclasses import dataclass

import chess
import chess.engine

from blunder_tutor.constants import MATE_SCORE_WEB
from blunder_tutor.utils.chess_utils import board_from_fen, format_eval


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


class AnalysisService:
    def __init__(self, engine: chess.engine.SimpleEngine, limit: chess.engine.Limit):
        self.engine = engine
        self.limit = limit

    def analyze_position(
        self, fen: str, player_color: str | None = None
    ) -> PositionAnalysis:
        board = chess.Board(fen)
        info = self.engine.analyse(board, self.limit)

        score = info.get("score")
        eval_cp = score.white().score(mate_score=MATE_SCORE_WEB) if score else 0

        pv = info.get("pv", [])
        best_move_uci = None
        best_move_san = None
        best_line = []

        if pv:
            best_move_uci = pv[0].uci()
            best_move_san = board.san(pv[0])

            # Build continuation line in SAN notation (up to 5 moves)
            temp_board = board.copy()
            for move in pv[:5]:
                best_line.append(temp_board.san(move))
                temp_board.push(move)

        eval_display = (
            format_eval(eval_cp, player_color) if player_color else str(eval_cp)
        )

        return PositionAnalysis(
            eval_cp=eval_cp,
            eval_display=eval_display,
            best_move_uci=best_move_uci,
            best_move_san=best_move_san,
            best_line=best_line,
        )

    def evaluate_move(
        self, fen: str, move_uci: str, player_color: str | None = None
    ) -> MoveEvaluation:
        board = board_from_fen(fen)

        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {move_uci}") from exc

        if move not in board.legal_moves:
            raise ValueError(f"Illegal move: {move_uci}")

        # Make the move and evaluate
        board.push(move)
        info = self.engine.analyse(board, self.limit)

        score = info.get("score")
        eval_cp = score.white().score(mate_score=MATE_SCORE_WEB) if score else 0

        eval_display = (
            format_eval(eval_cp, player_color) if player_color else str(eval_cp)
        )

        return MoveEvaluation(eval_cp=eval_cp, eval_display=eval_display)

    def get_move_san(self, fen: str, move_uci: str) -> str:
        board = board_from_fen(fen)
        try:
            move = chess.Move.from_uci(move_uci)
            return board.san(move)
        except ValueError as exc:
            raise ValueError(f"Invalid move: {move_uci}") from exc
