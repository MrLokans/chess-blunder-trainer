"""PGN file utility functions."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import chess
import chess.pgn

from blunder_tutor.utils.date_utils import parse_pgn_datetime_iso


def load_game(pgn_path: Path) -> chess.pgn.Game:
    with pgn_path.open("r", encoding="utf-8") as handle:
        game = chess.pgn.read_game(handle)
    if game is None:
        raise ValueError(f"Invalid PGN: {pgn_path}")
    return game


def load_game_from_string(pgn_content: str) -> chess.pgn.Game:
    stream = io.StringIO(pgn_content)
    game = chess.pgn.read_game(stream)
    if game is None:
        raise ValueError("Invalid PGN content")
    return game


def normalize_pgn(pgn_text: str) -> str:
    return pgn_text.strip().replace("\r\n", "\n").replace("\r", "\n") + "\n"


def compute_game_id(pgn_content: str) -> str:
    return hashlib.sha256(pgn_content.encode("utf-8")).hexdigest()


def build_game_metadata(
    pgn_text: str, source: str, username: str
) -> dict[str, str | None]:
    normalized = normalize_pgn(pgn_text)
    stream = io.StringIO(normalized)
    game = chess.pgn.read_game(stream)
    if game is None:
        return {}

    headers = dict(game.headers)
    date = headers.get("UTCDate") or headers.get("Date")
    time = headers.get("UTCTime") or headers.get("Time")
    end_time = parse_pgn_datetime_iso(date, time)

    return {
        "id": compute_game_id(normalized),
        "source": source,
        "username": username,
        "pgn_content": normalized,
        "date": headers.get("Date"),
        "end_time_utc": end_time,
        "white": headers.get("White"),
        "black": headers.get("Black"),
        "result": headers.get("Result"),
        "time_control": headers.get("TimeControl"),
    }


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
