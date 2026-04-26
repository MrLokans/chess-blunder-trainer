from __future__ import annotations

import chess
import chess.engine

# Display threshold: web-side mate scores use ±10000 (see MATE_SCORE_WEB
# in constants.py); evaluations beyond this are rendered as "M" rather
# than as a centipawn value.
DISPLAY_MATE_THRESHOLD = 10_000
CENTIPAWNS_PER_PAWN = 100


def board_from_fen(fen: str) -> chess.Board:
    return chess.Board(fen)


def format_eval(cp: int, player_color: str) -> str:
    """Format centipawn evaluation from player's perspective.

    Args:
        cp: Centipawn score (positive = good for white)
        player_color: "white" or "black"

    Returns:
        Formatted string like "+1.5", "-M", etc.
    """
    # Convert to player perspective
    if player_color == "black":
        cp = -cp
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
    """Convert chess.engine.PovScore to centipawns from perspective.

    Args:
        score: Engine score object
        side: chess.WHITE or chess.BLACK
        mate_score: Value to use for mate scores

    Returns:
        Centipawn value
    """
    if score is None:
        return 0
    return score.pov(side).score(mate_score=mate_score) or 0
