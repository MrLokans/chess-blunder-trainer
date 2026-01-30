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


class TestECODatabase:
    def test_classify_italian_game(self):
        board = _make_board_from_moves(["e4", "e5", "Nf3", "Nc6", "Bc4"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "C50"
        assert "Italian" in eco.name

    def test_classify_sicilian_defense(self):
        board = _make_board_from_moves(["e4", "c5"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "B20"
        assert "Sicilian" in eco.name

    def test_classify_sicilian_najdorf(self):
        board = _make_board_from_moves(
            ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]
        )
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "B90"
        assert "Najdorf" in eco.name

    def test_classify_ruy_lopez(self):
        board = _make_board_from_moves(["e4", "e5", "Nf3", "Nc6", "Bb5"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "C60"
        assert "Ruy Lopez" in eco.name

    def test_classify_queens_gambit(self):
        board = _make_board_from_moves(["d4", "d5", "c4"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "D06"
        assert "Queen's Gambit" in eco.name

    def test_classify_kings_indian(self):
        board = _make_board_from_moves(["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "E70"
        assert "King's Indian" in eco.name

    def test_classify_french_defense(self):
        board = _make_board_from_moves(["e4", "e6"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "C00"
        assert "French" in eco.name

    def test_classify_caro_kann(self):
        board = _make_board_from_moves(["e4", "c6"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "B10"
        assert "Caro-Kann" in eco.name

    def test_longest_match_wins(self):
        board = _make_board_from_moves(
            ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6", "Bg5"]
        )
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "B94"

    def test_empty_board_returns_none(self):
        board = chess.Board()
        eco = classify_opening(board)
        assert eco is None

    def test_single_move_e4(self):
        board = _make_board_from_moves(["e4"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "B00"

    def test_single_move_d4(self):
        board = _make_board_from_moves(["d4"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "A40"

    def test_english_opening(self):
        board = _make_board_from_moves(["c4"])
        eco = classify_opening(board)

        assert eco is not None
        assert eco.code == "A10"
        assert "English" in eco.name

    def test_database_is_cached(self):
        db1 = get_eco_database()
        db2 = get_eco_database()
        assert db1 is db2


class TestECOClassification:
    def test_frozen_dataclass(self):
        eco = ECOClassification(code="C50", name="Italian Game", moves="1. e4 e5")
        with pytest.raises(AttributeError):
            eco.code = "C51"
