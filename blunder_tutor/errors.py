from __future__ import annotations


class PuzzleNotFoundError(ValueError):
    """No stored analysis for the requested (game_id, ply)."""


class IllegalMoveError(ValueError):
    """The submitted move is malformed or illegal in the puzzle position."""
