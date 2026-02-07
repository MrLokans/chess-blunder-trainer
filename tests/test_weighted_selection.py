from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import chess
import chess.pgn
import pytest

from blunder_tutor.trainer import Trainer


def _make_blunder(
    game_id: str = "g1",
    ply: int = 10,
    player: int = 0,
    tactical_pattern: int | None = None,
    difficulty: int | None = None,
) -> dict:
    return {
        "game_id": game_id,
        "ply": ply,
        "player": player,
        "uci": "e2e4",
        "san": "e4",
        "eval_before": 50,
        "eval_after": -200,
        "cp_loss": 250,
        "best_move_uci": "d2d4",
        "best_move_san": "d4",
        "best_line": "d4 Nf6",
        "best_move_eval": 30,
        "game_phase": 1,
        "tactical_pattern": tactical_pattern,
        "tactical_reason": None,
        "difficulty": difficulty,
    }


@pytest.fixture
def trainer():
    games = MagicMock()
    attempts = MagicMock()
    analysis = MagicMock()
    return Trainer(games=games, attempts=attempts, analysis=analysis)


class TestComputeWeights:
    async def test_no_history_uniform_weights(self, trainer):
        candidates = [_make_blunder(ply=i) for i in range(5)]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates, "user1")
        assert all(w == 1.0 for w in weights)

    async def test_high_failure_rate_increases_weight(self, trainer):
        candidates = [
            _make_blunder(ply=1, tactical_pattern=1),
            _make_blunder(ply=2, tactical_pattern=2),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(
            return_value={1: 0.8, 2: 0.1}
        )
        weights = await trainer._compute_weights(candidates, "user1")
        assert weights[0] > weights[1]

    async def test_unseen_pattern_gets_exploration_bonus(self, trainer):
        candidates = [
            _make_blunder(ply=1, tactical_pattern=1),  # seen, 0% failure
            _make_blunder(ply=2, tactical_pattern=99),  # unseen
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={1: 0.0})
        weights = await trainer._compute_weights(candidates, "user1")
        assert weights[1] > weights[0]

    async def test_easy_difficulty_boosts_weight(self, trainer):
        candidates = [
            _make_blunder(ply=1, difficulty=20),
            _make_blunder(ply=2, difficulty=50),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates, "user1")
        assert weights[0] > weights[1]

    async def test_hard_difficulty_reduces_weight(self, trainer):
        candidates = [
            _make_blunder(ply=1, difficulty=50),
            _make_blunder(ply=2, difficulty=80),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates, "user1")
        assert weights[0] > weights[1]

    async def test_none_difficulty_no_effect(self, trainer):
        candidates = [
            _make_blunder(ply=1, difficulty=None),
            _make_blunder(ply=2, difficulty=None),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates, "user1")
        assert weights[0] == weights[1] == 1.0

    async def test_combined_pattern_and_difficulty(self, trainer):
        candidates = [
            _make_blunder(
                ply=1, tactical_pattern=1, difficulty=20
            ),  # high failure + easy
            _make_blunder(
                ply=2, tactical_pattern=2, difficulty=80
            ),  # low failure + hard
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(
            return_value={1: 0.9, 2: 0.1}
        )
        weights = await trainer._compute_weights(candidates, "user1")
        # Pattern 1: (1 + 0.9) * 1.3 = 2.47
        # Pattern 2: (1 + 0.1) * 0.7 = 0.77
        assert weights[0] > weights[1]
        assert weights[0] == pytest.approx(2.47, abs=0.01)
        assert weights[1] == pytest.approx(0.77, abs=0.01)
