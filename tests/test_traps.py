from __future__ import annotations

import chess

from blunder_tutor.analysis.traps import (
    TrapDatabase,
    TrapDefinition,
    _parse_pgn_to_san,
    get_trap_database,
)


def _make_board_from_pgn(pgn: str) -> chess.Board:
    moves = _parse_pgn_to_san(pgn)
    board = chess.Board()
    for m in moves:
        board.push_san(m)
    return board


def _scholars_mate_trap() -> TrapDefinition:
    return TrapDefinition(
        id="scholars_mate",
        name="Scholar's Mate",
        category="checkmate",
        rating_range=(0, 800),
        victim_side="black",
        entry_san_variants=[["e4", "e5", "Bc4", "Nc6", "Qh5"]],
        trap_san_variants=[["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"]],
        mistake_ply=6,
        mistake_san="Nf6",
        refutation_pgn="1. e4 e5 2. Bc4 Nc6 3. Qh5 g6 4. Qf3 Nf6",
        refutation_move="g6",
        refutation_note="Play g6.",
        recognition_tip="Watch for Qh5.",
        tags=["checkmate"],
    )


def _fried_liver_trap() -> TrapDefinition:
    return TrapDefinition(
        id="fried_liver",
        name="Fried Liver Attack",
        category="attack",
        rating_range=(0, 1400),
        victim_side="black",
        entry_san_variants=[["e4", "e5", "Nf3", "Nc6", "Bc4", "Nf6", "Ng5"]],
        trap_san_variants=[
            [
                "e4",
                "e5",
                "Nf3",
                "Nc6",
                "Bc4",
                "Nf6",
                "Ng5",
                "d5",
                "exd5",
                "Nxd5",
                "Nxf7",
            ]
        ],
        mistake_ply=10,
        mistake_san="Nxd5",
        refutation_pgn="1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Na5",
        refutation_move="Na5",
        refutation_note="Play Na5.",
        recognition_tip="Watch for Ng5.",
        tags=["sacrifice"],
    )


class TestParsePgnToSan:
    def test_simple_pgn(self):
        result = _parse_pgn_to_san("1. e4 e5 2. Nf3 Nc6")
        assert result == ["e4", "e5", "Nf3", "Nc6"]

    def test_pgn_with_result(self):
        result = _parse_pgn_to_san("1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#")
        assert result == ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]


class TestTrapDatabaseMatching:
    def test_scholars_mate_sprung_as_black(self):
        db = TrapDatabase([_scholars_mate_trap()])
        board = _make_board_from_pgn("1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#")
        matches = db.match_game(board, chess.BLACK)
        assert len(matches) == 1
        assert matches[0].trap_id == "scholars_mate"
        assert matches[0].match_type == "sprung"
        assert matches[0].user_was_victim is True
        assert matches[0].mistake_ply == 6

    def test_scholars_mate_executed_as_white(self):
        db = TrapDatabase([_scholars_mate_trap()])
        board = _make_board_from_pgn("1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#")
        matches = db.match_game(board, chess.WHITE)
        assert len(matches) == 1
        assert matches[0].match_type == "executed"
        assert matches[0].user_was_victim is False

    def test_entered_but_not_sprung(self):
        db = TrapDatabase([_scholars_mate_trap()])
        # Enters the trap line but plays g6 instead of Nf6
        board = _make_board_from_pgn("1. e4 e5 2. Bc4 Nc6 3. Qh5 g6 4. Qf3 Nf6")
        matches = db.match_game(board, chess.BLACK)
        assert len(matches) == 1
        assert matches[0].match_type == "entered"
        assert matches[0].mistake_ply is None

    def test_no_match(self):
        db = TrapDatabase([_scholars_mate_trap()])
        board = _make_board_from_pgn("1. d4 d5 2. c4 e6 3. Nc3 Nf6")
        matches = db.match_game(board, chess.WHITE)
        assert len(matches) == 0

    def test_fried_liver_sprung(self):
        db = TrapDatabase([_fried_liver_trap()])
        board = _make_board_from_pgn(
            "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7"
        )
        matches = db.match_game(board, chess.BLACK)
        assert len(matches) == 1
        assert matches[0].trap_id == "fried_liver"
        assert matches[0].match_type == "sprung"
        assert matches[0].user_was_victim is True

    def test_fried_liver_entered_with_na5(self):
        db = TrapDatabase([_fried_liver_trap()])
        board = _make_board_from_pgn(
            "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Na5"
        )
        matches = db.match_game(board, chess.BLACK)
        assert len(matches) == 1
        assert matches[0].match_type == "entered"

    def test_multiple_traps_in_db(self):
        db = TrapDatabase([_scholars_mate_trap(), _fried_liver_trap()])
        board = _make_board_from_pgn("1. d4 Nf6 2. c4 e6")
        matches = db.match_game(board, chess.WHITE)
        assert len(matches) == 0

    def test_get_trap(self):
        db = TrapDatabase([_scholars_mate_trap(), _fried_liver_trap()])
        assert db.get_trap("scholars_mate") is not None
        assert db.get_trap("fried_liver") is not None
        assert db.get_trap("nonexistent") is None


class TestTrapDatabaseLoading:
    def test_loads_from_fixture(self):
        db = get_trap_database()
        assert len(db.all_traps) > 0
        # Check a known trap exists
        trap = db.get_trap("scholars_mate")
        assert trap is not None
        assert trap.victim_side == "black"

    def test_all_traps_have_valid_entry_moves(self):
        db = get_trap_database()
        for trap in db.all_traps:
            assert len(trap.entry_san_variants) > 0
            for variant in trap.entry_san_variants:
                board = chess.Board()
                for m in variant:
                    board.push_san(m)

    def test_all_traps_have_valid_trap_moves(self):
        db = get_trap_database()
        for trap in db.all_traps:
            assert len(trap.trap_san_variants) > 0
            for variant in trap.trap_san_variants:
                board = chess.Board()
                for m in variant:
                    board.push_san(m)
