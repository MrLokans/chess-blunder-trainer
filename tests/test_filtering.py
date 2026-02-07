from __future__ import annotations

import pytest

from blunder_tutor.analysis.filtering import filter_blunders, is_valid_blunder
from blunder_tutor.constants import (
    ALREADY_LOST_THRESHOLD,
    MATE_THRESHOLD,
    STILL_WINNING_THRESHOLD,
)


def _blunder(
    eval_before: int = 50,
    eval_after: int = -200,
    game_id: str = "g1",
    player: int = 0,
) -> dict[str, object]:
    return {
        "game_id": game_id,
        "ply": 10,
        "player": player,
        "uci": "e2e4",
        "san": "e4",
        "eval_before": eval_before,
        "eval_after": eval_after,
        "cp_loss": max(0, eval_before - eval_after),
    }


class TestIsValidBlunder:
    def test_normal_blunder_is_valid(self):
        assert is_valid_blunder(_blunder(eval_before=100, eval_after=-150))

    def test_equal_to_losing_is_valid(self):
        assert is_valid_blunder(_blunder(eval_before=0, eval_after=-250))

    def test_slightly_winning_to_losing_is_valid(self):
        assert is_valid_blunder(_blunder(eval_before=200, eval_after=-50))

    def test_mate_delivery_filtered(self):
        assert not is_valid_blunder(
            _blunder(eval_before=MATE_THRESHOLD + 1, eval_after=500)
        )

    def test_eval_after_still_mate_filtered(self):
        assert not is_valid_blunder(
            _blunder(eval_before=500, eval_after=MATE_THRESHOLD + 1)
        )

    def test_already_lost_position_filtered(self):
        b = _blunder(eval_before=ALREADY_LOST_THRESHOLD - 1, eval_after=-800)
        assert not is_valid_blunder(b)

    def test_exactly_at_already_lost_threshold_filtered(self):
        b = _blunder(eval_before=ALREADY_LOST_THRESHOLD, eval_after=-600)
        assert not is_valid_blunder(b)

    def test_just_above_already_lost_threshold_valid(self):
        b = _blunder(eval_before=ALREADY_LOST_THRESHOLD + 1, eval_after=-600)
        assert is_valid_blunder(b)

    def test_still_winning_after_blunder_filtered(self):
        b = _blunder(eval_before=800, eval_after=STILL_WINNING_THRESHOLD + 1)
        assert not is_valid_blunder(b)

    def test_exactly_at_still_winning_threshold_filtered(self):
        b = _blunder(eval_before=800, eval_after=STILL_WINNING_THRESHOLD)
        assert not is_valid_blunder(b)

    def test_just_below_still_winning_threshold_valid(self):
        b = _blunder(eval_before=800, eval_after=STILL_WINNING_THRESHOLD - 1)
        assert is_valid_blunder(b)

    def test_deeply_lost_position_filtered(self):
        b = _blunder(eval_before=-600, eval_after=-900)
        assert not is_valid_blunder(b)

    def test_large_drop_but_still_comfortable_filtered(self):
        b = _blunder(eval_before=700, eval_after=400)
        assert not is_valid_blunder(b)

    def test_winning_to_equal_is_valid(self):
        b = _blunder(eval_before=250, eval_after=50)
        assert is_valid_blunder(b)

    def test_winning_to_losing_is_valid(self):
        b = _blunder(eval_before=200, eval_after=-200)
        assert is_valid_blunder(b)


class TestFilterBlunders:
    def test_filters_by_player_side(self):
        blunders = [
            _blunder(game_id="g1", player=0),
            _blunder(game_id="g1", player=1),
        ]
        game_side_map = {"g1": 0}
        result = filter_blunders(blunders, game_side_map)
        assert len(result) == 1
        assert result[0]["player"] == 0

    def test_filters_unknown_games(self):
        blunders = [_blunder(game_id="unknown")]
        result = filter_blunders(blunders, {"g1": 0})
        assert len(result) == 0

    def test_filters_invalid_blunders(self):
        blunders = [
            _blunder(eval_before=-500, eval_after=-800),  # already lost
            _blunder(eval_before=100, eval_after=-200),  # valid
        ]
        game_side_map = {"g1": 0}
        result = filter_blunders(blunders, game_side_map)
        assert len(result) == 1
        assert result[0]["eval_before"] == 100

    def test_combined_filtering(self):
        blunders = [
            _blunder(eval_before=100, eval_after=-200, game_id="g1", player=0),  # valid
            _blunder(
                eval_before=800, eval_after=400, game_id="g1", player=0
            ),  # still winning
            _blunder(
                eval_before=-400, eval_after=-700, game_id="g2", player=1
            ),  # already lost
            _blunder(eval_before=50, eval_after=-250, game_id="g2", player=1),  # valid
            _blunder(
                eval_before=50, eval_after=-100, game_id="g3", player=0
            ),  # wrong game
        ]
        game_side_map = {"g1": 0, "g2": 1}
        result = filter_blunders(blunders, game_side_map)
        assert len(result) == 2
        assert result[0]["eval_before"] == 100
        assert result[1]["eval_before"] == 50
