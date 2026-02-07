from __future__ import annotations

import chess

from blunder_tutor.analysis.pipeline.steps.move_quality import (
    compute_difficulty,
    _class_to_int,
)


def _board(fen: str = chess.STARTING_FEN) -> chess.Board:
    return chess.Board(fen)


class TestComputeDifficulty:
    def test_good_moves_have_zero_difficulty(self):
        board = _board()
        assert compute_difficulty(board, "e2e4", 0, _class_to_int("good")) == 0

    def test_quiet_best_move_scores_high(self):
        # Position where best move is a quiet retreat (not capture, not check)
        board = _board("r1bqkbnr/pppppppp/2n5/4N3/8/8/PPPPPPPP/RNBQKB1R b KQkq - 0 1")
        score = compute_difficulty(board, "d7d6", 250, _class_to_int("blunder"))
        assert score >= 40  # quiet move bonus

    def test_capture_best_move_scores_lower(self):
        # Position where best move is a capture
        board = _board("r1bqkbnr/pppppppp/2n5/4N3/8/8/PPPPPPPP/RNBQKB1R b KQkq - 0 1")
        score = compute_difficulty(board, "c6e5", 250, _class_to_int("blunder"))
        assert score < 40  # capture = easier to see

    def test_check_best_move_scores_lowest(self):
        # Position where best move gives check
        board = _board(
            "rnbqk2r/pppp1ppp/5n2/2b1p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 1"
        )
        score = compute_difficulty(board, "f3f7", 300, _class_to_int("blunder"))
        assert score <= 20  # check = very visible

    def test_few_legal_moves_increases_difficulty(self):
        # King boxed in corner with few legal moves
        board = _board("8/8/8/8/8/8/1q6/K7 w - - 0 1")
        legal_count = board.legal_moves.count()
        assert legal_count <= 3
        score = compute_difficulty(board, "a1b2", 250, _class_to_int("blunder"))
        # capture (15) + few moves (30) = 45
        assert score >= 40

    def test_many_legal_moves_lower_difficulty(self):
        board = _board()
        score = compute_difficulty(board, "e2e4", 250, _class_to_int("blunder"))
        # 20 legal moves in starting position, quiet move
        # Should get quiet bonus (40) but no legal-move bonus
        assert score == 40

    def test_no_best_move_returns_default(self):
        board = _board()
        assert compute_difficulty(board, None, 250, _class_to_int("blunder")) == 50

    def test_invalid_uci_returns_default(self):
        board = _board()
        assert compute_difficulty(board, "zzzz", 250, _class_to_int("blunder")) == 50

    def test_capped_at_100(self):
        # Few legal moves + quiet move + high cp_loss = all bonuses stacking
        board = _board("8/8/8/8/8/6k1/8/5K2 w - - 0 1")
        score = compute_difficulty(board, "f1e1", 500, _class_to_int("blunder"))
        assert score <= 100

    def test_large_cp_loss_quiet_move_bonus(self):
        board = _board("r1bqkbnr/pppppppp/2n5/4N3/8/8/PPPPPPPP/RNBQKB1R b KQkq - 0 1")
        low_loss = compute_difficulty(board, "d7d6", 200, _class_to_int("blunder"))
        high_loss = compute_difficulty(board, "d7d6", 500, _class_to_int("blunder"))
        assert high_loss > low_loss
