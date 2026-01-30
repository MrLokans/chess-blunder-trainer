from __future__ import annotations

import chess

from blunder_tutor.constants import PHASE_ENDGAME, PHASE_MIDDLEGAME, PHASE_OPENING


def classify_phase(board: chess.Board, move_number: int) -> int:
    piece_count = len(board.piece_map()) - 2  # Exclude kings

    if move_number <= 10 and piece_count >= 20:
        return PHASE_OPENING
    if move_number <= 15 and piece_count >= 16:
        return PHASE_OPENING
    if piece_count <= 6:
        return PHASE_ENDGAME
    if piece_count <= 10 and move_number > 30:
        return PHASE_ENDGAME
    return PHASE_MIDDLEGAME
