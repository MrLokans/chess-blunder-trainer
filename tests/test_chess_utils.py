from __future__ import annotations

import chess
import chess.engine
import pytest

from blunder_tutor.utils.chess_utils import board_from_fen, format_eval, score_to_cp


class TestBoardFromFen:
    def test_valid_starting_position(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        board = board_from_fen(fen)
        assert isinstance(board, chess.Board)
        assert board.fen() == fen

    def test_valid_custom_position(self):
        fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
        board = board_from_fen(fen)
        assert isinstance(board, chess.Board)
        assert board.fen() == fen

    def test_invalid_fen(self):
        with pytest.raises(ValueError):
            board_from_fen("invalid fen string")

    def test_empty_board(self):
        fen = "8/8/8/8/8/8/8/8 w - - 0 1"
        board = board_from_fen(fen)
        assert isinstance(board, chess.Board)


class TestFormatEval:
    def test_white_winning(self):
        assert format_eval(150, "white") == "+1.5"
        assert format_eval(50, "white") == "+0.5"
        assert format_eval(100, "white") == "+1.0"

    def test_white_losing(self):
        assert format_eval(-150, "white") == "-1.5"
        assert format_eval(-50, "white") == "-0.5"

    def test_black_perspective(self):
        assert format_eval(150, "black") == "-1.5"
        assert format_eval(-150, "black") == "+1.5"
        assert format_eval(0, "black") == "0.0"

    def test_mate_score_positive(self):
        assert format_eval(15000, "white") == "+M"
        assert format_eval(10000, "white") == "+M"
        assert format_eval(100000, "white") == "+M"

    def test_mate_score_negative(self):
        assert format_eval(-15000, "white") == "-M"
        assert format_eval(-10000, "white") == "-M"

    def test_even_position(self):
        assert format_eval(0, "white") == "0.0"
        assert format_eval(0, "black") == "0.0"

    def test_small_advantage(self):
        assert format_eval(25, "white") == "+0.2"
        assert format_eval(-25, "white") == "-0.2"


class TestScoreToCp:
    def test_none_score(self):
        assert score_to_cp(None, chess.WHITE) == 0
        assert score_to_cp(None, chess.BLACK) == 0

    def test_cp_score_white(self):
        score = chess.engine.PovScore(chess.engine.Cp(150), chess.WHITE)
        assert score_to_cp(score, chess.WHITE) == 150

    def test_cp_score_black(self):
        score = chess.engine.PovScore(chess.engine.Cp(150), chess.BLACK)
        assert score_to_cp(score, chess.BLACK) == 150

    def test_mate_score_default(self):
        score = chess.engine.PovScore(chess.engine.Mate(1), chess.WHITE)
        result = score_to_cp(score, chess.WHITE)
        # Mate in 1 should give us the mate_score value
        assert result > 0
        assert abs(result) >= 10000  # At least a very high score

    def test_mate_score_custom(self):
        score = chess.engine.PovScore(chess.engine.Mate(1), chess.WHITE)
        result = score_to_cp(score, chess.WHITE, mate_score=10000)
        # Mate should give us a very high score
        assert result > 0
        assert abs(result) >= 5000

    def test_perspective_flip(self):
        score = chess.engine.PovScore(chess.engine.Cp(150), chess.WHITE)
        # From black's perspective, this should be negative
        result = score_to_cp(score, chess.BLACK)
        assert result == -150
