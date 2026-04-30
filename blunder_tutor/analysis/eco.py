from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chess

from blunder_tutor.constants import DEFAULT_FIXTURES_PATH

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ECOClassification:
    code: str
    name: str
    moves: str


class ECODatabase:
    def __init__(self, entries: dict[str, ECOClassification]):
        self._positions = entries

    def classify(self, board: chess.Board) -> ECOClassification | None:
        cursor = board.copy()
        while True:
            match = self._positions.get(cursor.epd())
            if match is not None:
                return match
            if not cursor.move_stack:
                return None
            cursor.pop()


def _strip_move_number(token: str) -> str | None:
    """Return the SAN portion of a PGN token, or None if the token has no move."""
    if token.endswith(".") or (token[0].isdigit() and "." not in token):
        return None
    if "." in token:
        stripped = token.split(".")[-1]
        return stripped or None
    return token


def _parse_pgn_moves(pgn: str) -> chess.Board | None:
    board = chess.Board()
    try:
        for token in pgn.split():
            san = _strip_move_number(token)
            if san is not None:
                board.push_san(san)
    except (ValueError, chess.InvalidMoveError, chess.AmbiguousMoveError):
        return None
    return board


def _load_eco_entries(path: Path) -> dict[str, ECOClassification]:
    positions: dict[str, ECOClassification] = {}
    move_counts: dict[str, int] = {}

    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            board = _parse_pgn_moves(row["pgn"])
            if board is None:
                logger.warning(
                    "Skipping invalid ECO entry: %s %s", row["eco"], row["name"]
                )
                continue

            epd = board.epd()
            num_moves = len(board.move_stack)
            if epd not in positions or num_moves >= move_counts[epd]:
                positions[epd] = ECOClassification(
                    code=row["eco"], name=row["name"], moves=row["pgn"]
                )
                move_counts[epd] = num_moves

    return positions


@lru_cache(maxsize=1)
def get_eco_database(path: Path | None = None) -> ECODatabase:
    if path is None:
        path = DEFAULT_FIXTURES_PATH / "eco.tsv"
    entries = _load_eco_entries(path)
    return ECODatabase(entries)


def classify_opening(board: chess.Board) -> ECOClassification | None:
    db = get_eco_database()
    return db.classify(board)
