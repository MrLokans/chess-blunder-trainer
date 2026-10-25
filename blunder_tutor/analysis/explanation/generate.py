from __future__ import annotations

import chess

from blunder_tutor.analysis.explanation.best import explain_best
from blunder_tutor.analysis.explanation.blunder import explain_blunder
from blunder_tutor.analysis.explanation.messages import BlunderExplanation
from blunder_tutor.analysis.explanation.puzzle import Puzzle
from blunder_tutor.utils.chess_utils import board_from_fen


def _parse_legal_move(board: chess.Board, uci: str | None) -> chess.Move | None:
    if not uci:
        return None
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return None
    if move not in board.legal_moves:
        return None
    return move


def generate_explanation(
    fen: str,
    blunder_uci: str,
    best_move_uci: str | None,
    cp_loss: int = 0,
    best_line: list[str] | None = None,
    refutation_line: list[str] | None = None,
) -> BlunderExplanation:
    board = board_from_fen(fen)
    blunder_move = _parse_legal_move(board, blunder_uci)
    if blunder_move is None:
        return BlunderExplanation(blunder=None, best_move=None)
    puzzle = Puzzle(
        board=board,
        blunder_move=blunder_move,
        best_move=_parse_legal_move(board, best_move_uci),
        cp_loss=cp_loss,
        best_line=best_line,
        refutation_line=refutation_line,
    )
    return BlunderExplanation(
        blunder=explain_blunder(puzzle), best_move=explain_best(puzzle)
    )
