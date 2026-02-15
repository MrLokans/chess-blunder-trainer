"""Shared factory functions for test data."""

from __future__ import annotations

import chess
import chess.pgn


def make_blunder(
    game_id: str = "g1",
    ply: int = 10,
    player: int = 0,
    uci: str = "e2e4",
    san: str = "e4",
    eval_before: int = 50,
    eval_after: int = -200,
    cp_loss: int = 250,
    best_move_uci: str | None = "d2d4",
    best_move_san: str | None = "d4",
    best_line: str | None = "d4 Nf6",
    best_move_eval: int | None = 30,
    game_phase: int | None = 1,
    tactical_pattern: int | None = None,
    tactical_reason: str | None = None,
    difficulty: int | None = None,
) -> dict:
    return {
        "game_id": game_id,
        "ply": ply,
        "player": player,
        "uci": uci,
        "san": san,
        "eval_before": eval_before,
        "eval_after": eval_after,
        "cp_loss": cp_loss,
        "best_move_uci": best_move_uci,
        "best_move_san": best_move_san,
        "best_line": best_line,
        "best_move_eval": best_move_eval,
        "game_phase": game_phase,
        "tactical_pattern": tactical_pattern,
        "tactical_reason": tactical_reason,
        "difficulty": difficulty,
    }


STANDARD_MOVES = [
    chess.Move.from_uci("e2e4"),
    chess.Move.from_uci("e7e5"),
    chess.Move.from_uci("g1f3"),
    chess.Move.from_uci("b8c6"),
    chess.Move.from_uci("f1c4"),
    chess.Move.from_uci("g8f6"),
    chess.Move.from_uci("d2d3"),
    chess.Move.from_uci("f8c5"),
    chess.Move.from_uci("c2c3"),
    chess.Move.from_uci("d7d6"),
]


def make_mock_game(
    n_moves: int = 10,
    headers: dict[str, str] | None = None,
) -> chess.pgn.Game:
    from unittest.mock import MagicMock

    mock_game = MagicMock(spec=chess.pgn.Game)
    mock_game.headers = headers or {}
    mock_game.board.return_value = chess.Board()
    mock_game.mainline_moves.return_value = STANDARD_MOVES[:n_moves]
    return mock_game
