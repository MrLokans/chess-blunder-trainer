from __future__ import annotations

import chess
import chess.engine


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
    if cp >= 10000:
        return "+M"
    if cp <= -10000:
        return "-M"
    sign = "+" if cp > 0 else ""
    return f"{sign}{cp / 100:.1f}"


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
