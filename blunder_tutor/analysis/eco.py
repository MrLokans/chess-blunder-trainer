from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chess

from blunder_tutor.constants import DEFAULT_FIXTURES_PATH


@dataclass(frozen=True)
class ECOClassification:
    code: str
    name: str
    moves: str


class ECODatabase:
    def __init__(self, entries: list[tuple[str, ECOClassification]]):
        self._entries = sorted(entries, key=lambda x: -len(x[0]))

    def classify(self, board: chess.Board) -> ECOClassification | None:
        moves_san = self._extract_moves_san(board)
        if not moves_san:
            return None

        for prefix, eco in self._entries:
            if moves_san.startswith(prefix):
                return eco
        return None

    def _extract_moves_san(self, board: chess.Board) -> str:
        moves = []
        temp_board = board.root()
        for move in board.move_stack:
            try:
                san = temp_board.san(move)
            except (AssertionError, ValueError):
                break
            moves.append(san)
            temp_board.push(move)
        return " ".join(moves)


def _parse_pgn_moves(pgn: str) -> str:
    parts = pgn.split()
    moves = []
    for part in parts:
        if part.endswith("."):
            continue
        if part[0].isdigit() and "." in part:
            part = part.split(".")[-1]
            if part:
                moves.append(part)
        else:
            moves.append(part)
    return " ".join(moves)


def _load_eco_entries(path: Path) -> list[tuple[str, ECOClassification]]:
    entries = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            eco_code = row["eco"]
            name = row["name"]
            pgn = row["pgn"]
            moves_san = _parse_pgn_moves(pgn)
            eco = ECOClassification(code=eco_code, name=name, moves=pgn)
            entries.append((moves_san, eco))
    return entries


@lru_cache(maxsize=1)
def get_eco_database(path: Path | None = None) -> ECODatabase:
    if path is None:
        path = DEFAULT_FIXTURES_PATH / "eco.tsv"
    entries = _load_eco_entries(path)
    return ECODatabase(entries)


def classify_opening(board: chess.Board) -> ECOClassification | None:
    db = get_eco_database()
    return db.classify(board)
