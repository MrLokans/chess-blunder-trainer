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


VALID_BLUNDER_CASES = [
    (100, -150, "normal blunder"),
    (0, -250, "equal to losing"),
    (200, -50, "slightly winning to losing"),
    (ALREADY_LOST_THRESHOLD + 1, -600, "just above already-lost threshold"),
    (800, STILL_WINNING_THRESHOLD - 1, "just below still-winning threshold"),
    (250, 50, "winning to equal"),
    (200, -200, "winning to losing"),
]

FILTERED_BLUNDER_CASES = [
    (MATE_THRESHOLD + 1, 500, "mate delivery"),
    (500, MATE_THRESHOLD + 1, "eval after still mate"),
    (ALREADY_LOST_THRESHOLD - 1, -800, "already lost position"),
    (ALREADY_LOST_THRESHOLD, -600, "exactly at already-lost threshold"),
    (800, STILL_WINNING_THRESHOLD + 1, "still winning after blunder"),
    (800, STILL_WINNING_THRESHOLD, "exactly at still-winning threshold"),
    (-600, -900, "deeply lost position"),
    (700, 400, "large drop but still comfortable"),
]


class TestIsValidBlunder:
    @pytest.mark.parametrize("eval_before,eval_after,desc", VALID_BLUNDER_CASES)
    def test_valid_blunders(self, eval_before, eval_after, desc):
        assert is_valid_blunder(
            _blunder(eval_before=eval_before, eval_after=eval_after)
        )

    @pytest.mark.parametrize("eval_before,eval_after,desc", FILTERED_BLUNDER_CASES)
    def test_filtered_blunders(self, eval_before, eval_after, desc):
        assert not is_valid_blunder(
            _blunder(eval_before=eval_before, eval_after=eval_after)
        )


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
            _blunder(eval_before=-500, eval_after=-800),
            _blunder(eval_before=100, eval_after=-200),
        ]
        game_side_map = {"g1": 0}
        result = filter_blunders(blunders, game_side_map)
        assert len(result) == 1
        assert result[0]["eval_before"] == 100

    def test_combined_filtering(self):
        blunders = [
            _blunder(eval_before=100, eval_after=-200, game_id="g1", player=0),
            _blunder(eval_before=800, eval_after=400, game_id="g1", player=0),
            _blunder(eval_before=-400, eval_after=-700, game_id="g2", player=1),
            _blunder(eval_before=50, eval_after=-250, game_id="g2", player=1),
            _blunder(eval_before=50, eval_after=-100, game_id="g3", player=0),
        ]
        game_side_map = {"g1": 0, "g2": 1}
        result = filter_blunders(blunders, game_side_map)
        assert len(result) == 2
        assert result[0]["eval_before"] == 100
        assert result[1]["eval_before"] == 50
