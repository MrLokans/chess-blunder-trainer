from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from blunder_tutor.trainer import Trainer
from tests.helpers.factories import make_blunder


@pytest.fixture
def trainer():
    games = MagicMock()
    attempts = MagicMock()
    analysis = MagicMock()
    return Trainer(games=games, attempts=attempts, analysis=analysis)


class TestComputeWeights:
    async def test_no_history_uniform_weights(self, trainer):
        candidates = [make_blunder(ply=i) for i in range(5)]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert all(w == 1.0 for w in weights)

    async def test_high_failure_rate_increases_weight(self, trainer):
        candidates = [
            make_blunder(ply=1, tactical_pattern=1),
            make_blunder(ply=2, tactical_pattern=2),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(
            return_value={1: 0.8, 2: 0.1}
        )
        weights = await trainer._compute_weights(candidates)
        assert weights[0] > weights[1]

    async def test_unseen_pattern_gets_exploration_bonus(self, trainer):
        candidates = [
            make_blunder(ply=1, tactical_pattern=1),  # seen, 0% failure
            make_blunder(ply=2, tactical_pattern=99),  # unseen
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={1: 0.0})
        weights = await trainer._compute_weights(candidates)
        assert weights[1] > weights[0]

    async def test_easy_difficulty_boosts_weight(self, trainer):
        candidates = [
            make_blunder(ply=1, difficulty=20),
            make_blunder(ply=2, difficulty=50),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert weights[0] > weights[1]

    async def test_hard_difficulty_reduces_weight(self, trainer):
        candidates = [
            make_blunder(ply=1, difficulty=50),
            make_blunder(ply=2, difficulty=80),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert weights[0] > weights[1]

    async def test_none_difficulty_no_effect(self, trainer):
        candidates = [
            make_blunder(ply=1, difficulty=None),
            make_blunder(ply=2, difficulty=None),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert weights[0] == weights[1] == 1.0

    async def test_combined_pattern_and_difficulty(self, trainer):
        candidates = [
            make_blunder(
                ply=1, tactical_pattern=1, difficulty=20
            ),  # high failure + easy
            make_blunder(
                ply=2, tactical_pattern=2, difficulty=80
            ),  # low failure + hard
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(
            return_value={1: 0.9, 2: 0.1}
        )
        weights = await trainer._compute_weights(candidates)
        # Pattern 1: (1 + 0.9) * 1.3 = 2.47
        # Pattern 2: (1 + 0.1) * 0.7 = 0.77
        assert weights[0] > weights[1]
        assert weights[0] == pytest.approx(2.47, abs=0.01)
        assert weights[1] == pytest.approx(0.77, abs=0.01)
