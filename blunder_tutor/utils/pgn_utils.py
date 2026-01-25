"""PGN file utility functions."""

from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn


def load_game(pgn_path: Path) -> chess.pgn.Game:
    with pgn_path.open("r", encoding="utf-8") as handle:
        game = chess.pgn.read_game(handle)
    if game is None:
        raise ValueError(f"Invalid PGN: {pgn_path}")
    return game


def board_before_ply(game: chess.pgn.Game, target_ply: int) -> chess.Board:
    """Get the board state before a specific ply.

    Args:
        game: Chess game
        target_ply: The ply number (1-indexed)

    Returns:
        Board state before the target ply

    Raises:
        ValueError: If the target ply is not found in the game
    """
    board = game.board()
    ply = 1
    for move in game.mainline_moves():
        if ply == target_ply:
            return board
        board.push(move)
        ply += 1
    raise ValueError(f"Ply not found: {target_ply}")
