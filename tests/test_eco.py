from __future__ import annotations

import chess
import pytest

from blunder_tutor.analysis.eco import (
    ECOClassification,
    classify_opening,
    get_eco_database,
)


def _make_board_from_moves(moves: list[str]) -> chess.Board:
    board = chess.Board()
    for move in moves:
        board.push_san(move)
    return board


OPENING_CASES = [
    (["e4", "e5", "Nf3", "Nc6", "Bc4"], "C50", "Italian"),
    (["e4", "c5"], "B20", "Sicilian"),
    (
        ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
        "B90",
        "Najdorf",
    ),
    (["e4", "e5", "Nf3", "Nc6", "Bb5"], "C60", "Ruy Lopez"),
    (["d4", "d5", "c4"], "D06", "Queen's Gambit"),
    (["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4"], "E70", "King's Indian"),
    (["e4", "e6"], "C00", "French"),
    (["e4", "c6"], "B10", "Caro-Kann"),
    (["c4"], "A10", "English"),
]


class TestECODatabase:
    @pytest.mark.parametrize("moves,expected_code,expected_name", OPENING_CASES)
    def test_classify_opening(self, moves, expected_code, expected_name):
        board = _make_board_from_moves(moves)
        eco = classify_opening(board)
        assert eco is not None
        assert eco.code == expected_code
        assert expected_name in eco.name

    def test_longest_match_wins(self):
        board = _make_board_from_moves(
            ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6", "Bg5"]
        )
        eco = classify_opening(board)
        assert eco is not None
        assert eco.code == "B94"

    def test_empty_board_returns_none(self):
        board = chess.Board()
        assert classify_opening(board) is None

    @pytest.mark.parametrize(
        "moves,expected_code",
        [
            (["e4"], "B00"),
            (["d4"], "A40"),
        ],
    )
    def test_single_move(self, moves, expected_code):
        board = _make_board_from_moves(moves)
        eco = classify_opening(board)
        assert eco is not None
        assert eco.code == expected_code

    def test_database_is_cached(self):
        db1 = get_eco_database()
        db2 = get_eco_database()
        assert db1 is db2


class TestECOClassification:
    def test_frozen_dataclass(self):
        eco = ECOClassification(code="C50", name="Italian Game", moves="1. e4 e5")
        with pytest.raises(AttributeError):
            eco.code = "C51"
