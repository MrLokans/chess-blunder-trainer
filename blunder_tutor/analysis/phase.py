from __future__ import annotations

import chess

from blunder_tutor.constants import PHASE_ENDGAME, PHASE_MIDDLEGAME, PHASE_OPENING

# Phase classification heuristics. Tuned by manual review against
# annotated games; the boundaries reflect typical material/move-count
# transitions (e.g., few captures + many pieces in early moves =
# opening; lots of captures + few pieces = endgame).
KING_COUNT = 2
OPENING_EARLY_MOVE_LIMIT = 10
OPENING_EARLY_PIECE_FLOOR = 20
OPENING_LATE_MOVE_LIMIT = 15
OPENING_LATE_PIECE_FLOOR = 16
ENDGAME_PIECE_CEILING = 6
ENDGAME_LATE_PIECE_CEILING = 10
ENDGAME_LATE_MOVE_FLOOR = 30


def classify_phase(board: chess.Board, move_number: int) -> int:
    piece_count = len(board.piece_map()) - KING_COUNT

    if (
        move_number <= OPENING_EARLY_MOVE_LIMIT
        and piece_count >= OPENING_EARLY_PIECE_FLOOR
    ):
        return PHASE_OPENING
    if (
        move_number <= OPENING_LATE_MOVE_LIMIT
        and piece_count >= OPENING_LATE_PIECE_FLOOR
    ):
        return PHASE_OPENING
    if piece_count <= ENDGAME_PIECE_CEILING:
        return PHASE_ENDGAME
    if (
        piece_count <= ENDGAME_LATE_PIECE_CEILING
        and move_number > ENDGAME_LATE_MOVE_FLOOR
    ):
        return PHASE_ENDGAME
    return PHASE_MIDDLEGAME
