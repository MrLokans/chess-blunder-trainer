from __future__ import annotations

import pytest

from blunder_tutor.utils.accuracy import game_accuracy, move_accuracy, win_percent_drop


class TestWinPercentDrop:
    def test_matches_lichess_win_percent_at_one_pawn(self):
        # Lichess: +100cp is a 59.1% win chance, so dropping to 0.00 loses ~9.1%.
        assert win_percent_drop(100, 0) == pytest.approx(9.1, abs=0.05)

    def test_improving_move_is_no_drop(self):
        assert win_percent_drop(0, 50) == 0.0

    def test_same_cp_loss_costs_less_in_a_decided_position(self):
        assert win_percent_drop(-500, -550) < win_percent_drop(0, -50)

    def test_mate_scores_saturate(self):
        assert win_percent_drop(100_000, -100_000) == pytest.approx(95.1, abs=0.1)


class TestMoveAccuracy:
    def test_perfect_move(self):
        assert move_accuracy(0) == 100.0

    def test_half_pawn_inaccuracy_from_equal(self):
        # Previously fed raw cp_loss=50 and scored ~8.5%.
        assert move_accuracy(win_percent_drop(0, -50)) == pytest.approx(81.3, abs=0.1)

    def test_large_drop_near_zero(self):
        assert move_accuracy(95) == pytest.approx(0.0, abs=0.1)

    def test_monotonically_decreasing(self):
        drops = [0, 1, 5, 10, 25, 50, 100]
        accuracies = [move_accuracy(d) for d in drops]
        assert accuracies == sorted(accuracies, reverse=True)


class TestGameAccuracy:
    def test_empty_list(self):
        assert game_accuracy([]) == 0.0

    def test_all_perfect_moves(self):
        assert game_accuracy([(0, 0), (30, 40), (-20, -20)]) == 100.0

    def test_mean_of_move_accuracies(self):
        moves = [(0, 0), (100, 0)]
        expected = (100.0 + move_accuracy(win_percent_drop(100, 0))) / 2
        assert game_accuracy(moves) == pytest.approx(expected)
