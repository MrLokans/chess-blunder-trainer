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
        for _ in range(len(cursor.move_stack)):
            match = self._positions.get(cursor.epd())
            if match is not None:
                return match
            cursor.pop()

        return self._positions.get(cursor.epd())


def _load_eco_entries(path: Path) -> dict[str, ECOClassification]:
    positions: dict[str, ECOClassification] = {}
    move_counts: dict[str, int] = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            eco_code = row["eco"]
            name = row["name"]
            pgn = row["pgn"]

            try:
                board = chess.Board()
                for token in pgn.split():
                    if token.endswith(".") or (token[0].isdigit() and "." not in token):
                        continue
                    if "." in token:
                        token = token.split(".")[-1]
                        if not token:
                            continue
                    board.push_san(token)
            except (ValueError, chess.InvalidMoveError, chess.AmbiguousMoveError):
                logger.warning("Skipping invalid ECO entry: %s %s", eco_code, name)
                continue

            epd = board.epd()
            num_moves = len(board.move_stack)

            if epd not in positions or num_moves >= move_counts[epd]:
                positions[epd] = ECOClassification(code=eco_code, name=name, moves=pgn)
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
