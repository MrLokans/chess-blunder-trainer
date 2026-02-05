from __future__ import annotations

import pytest

from blunder_tutor.utils.accuracy import game_accuracy, move_accuracy


class TestMoveAccuracy:
    def test_perfect_move(self):
        assert move_accuracy(0) == pytest.approx(100.0, abs=0.1)

    def test_negative_cp_loss_treated_as_perfect(self):
        assert move_accuracy(-10) == 100.0

    def test_small_loss(self):
        result = move_accuracy(25)
        assert 25 < result < 50

    def test_medium_loss(self):
        result = move_accuracy(50)
        assert 5 < result < 25

    def test_large_loss_near_zero(self):
        result = move_accuracy(500)
        assert result == pytest.approx(0.0, abs=0.1)

    def test_monotonically_decreasing(self):
        prev = 100.0
        for cp in [0, 10, 25, 50, 100, 200, 500]:
            acc = move_accuracy(cp)
            assert acc <= prev
            prev = acc


class TestGameAccuracy:
    def test_empty_list(self):
        assert game_accuracy([]) == 0.0

    def test_all_perfect_moves(self):
        assert game_accuracy([0, 0, 0]) == pytest.approx(100.0, abs=0.1)

    def test_mixed_moves(self):
        result = game_accuracy([0, 50, 100, 200])
        assert 20 < result < 80

    def test_single_move(self):
        assert game_accuracy([0]) == pytest.approx(move_accuracy(0), abs=0.01)
        assert game_accuracy([100]) == pytest.approx(move_accuracy(100), abs=0.01)

    def test_all_blunders(self):
        result = game_accuracy([500, 500, 500])
        assert result == pytest.approx(0.0, abs=0.5)
