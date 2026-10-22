from __future__ import annotations

import chess
import chess.engine

# Display threshold: web-side mate scores use ±10000 (see MATE_SCORE_WEB
# in constants.py); evaluations beyond this are rendered as "M" rather
# than as a centipawn value.
DISPLAY_MATE_THRESHOLD = 10_000
CENTIPAWNS_PER_PAWN = 100


def board_from_fen(fen: str) -> chess.Board:
    """Chess960 mode only when the castling rights need it: a plain standard board drops
    non-standard rights, making legal Chess960 castling look illegal."""
    board = chess.Board(fen, chess960=True)
    board.chess960 = board.has_chess960_castling_rights()
    return board


def format_eval(cp: int) -> str:
    """`cp` must already be from the player's perspective, e.g. `+1.5` or `-M`."""
    if cp >= DISPLAY_MATE_THRESHOLD:
        return "+M"
    if cp <= -DISPLAY_MATE_THRESHOLD:
        return "-M"
    sign = "+" if cp > 0 else ""
    return f"{sign}{cp / CENTIPAWNS_PER_PAWN:.1f}"


def score_to_cp(
    score: chess.engine.PovScore | None,
    side: chess.Color,
    mate_score: int = 100000,
) -> int:
    if score is None:
        return 0
    return score.pov(side).score(mate_score=mate_score) or 0
