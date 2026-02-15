from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from blunder_tutor.analysis.filtering import is_valid_blunder
from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.pipeline.steps.move_quality import (
    MoveQualityStep,
    _class_to_int,
    _get_mate_depth,
)
from blunder_tutor.analysis.thresholds import Thresholds
from blunder_tutor.constants import (
    LONG_MATE_DEPTH_THRESHOLD,
    MATE_SCORE_ANALYSIS,
    MAX_CP_LOSS,
)
from blunder_tutor.trainer import Trainer


def _make_pov_score(cp: int | None = None, mate: int | None = None) -> MagicMock:
    score = MagicMock()
    pov = MagicMock()
    if mate is not None:
        pov.is_mate.return_value = True
        pov.mate.return_value = mate
        pov.score.return_value = (
            MATE_SCORE_ANALYSIS if mate > 0 else -MATE_SCORE_ANALYSIS
        )
    else:
        pov.is_mate.return_value = False
        pov.mate.return_value = None
        pov.score.return_value = cp or 0
    score.pov.return_value = pov
    return score


def _move_eval(
    *,
    eval_before: int,
    eval_after: int,
    score_before: MagicMock | None = None,
    ply: int = 1,
) -> dict:
    import chess

    if score_before is None:
        score_before = _make_pov_score(cp=eval_before)
    return {
        "ply": ply,
        "move_number": 1,
        "player": "white",
        "uci": "e2e4",
        "san": "e4",
        "eval_before": eval_before,
        "eval_after": eval_after,
        "info_before": {"score": score_before},
        "best_move_uci": "d2d4",
        "best_move_san": "d4",
        "best_line": "d4 Nf6",
        "best_move_eval": eval_before,
        "board": chess.Board(),
    }


def _mock_context(move_evals: list[dict]) -> StepContext:
    ctx = StepContext(
        game_id="test",
        game=MagicMock(),
        analysis_repo=AsyncMock(),
        game_repo=AsyncMock(),
        engine_path="/path/to/engine",
        thresholds=Thresholds(),
        depth=14,
    )
    stockfish_result = StepResult(
        step_id="stockfish",
        success=True,
        data={"move_evals": move_evals},
    )
    ctx.add_step_result(stockfish_result)
    return ctx


class TestGetMateDepth:
    def test_returns_none_for_non_mate(self):
        import chess

        score = _make_pov_score(cp=150)
        assert _get_mate_depth(score, chess.WHITE) is None

    def test_returns_depth_for_mate(self):
        import chess

        score = _make_pov_score(mate=3)
        assert _get_mate_depth(score, chess.WHITE) == 3

    def test_returns_negative_for_getting_mated(self):
        import chess

        score = _make_pov_score(mate=-2)
        assert _get_mate_depth(score, chess.WHITE) == -2


class TestCpLossCapping:
    async def test_normal_cp_loss_not_capped(self):
        move = _move_eval(eval_before=300, eval_after=0)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        assert result.data["moves"][0]["cp_loss"] == 300

    async def test_cp_loss_capped_at_max(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=200,
            score_before=_make_pov_score(mate=3),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        assert result.data["moves"][0]["cp_loss"] == MAX_CP_LOSS

    async def test_large_non_mate_loss_also_capped(self):
        move = _move_eval(eval_before=5000, eval_after=-5000)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        assert result.data["moves"][0]["cp_loss"] == MAX_CP_LOSS


class TestMissedMateDepth:
    async def test_no_mate_before_returns_none(self):
        move = _move_eval(eval_before=300, eval_after=-100)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        assert result.data["moves"][0]["missed_mate_depth"] is None

    async def test_mate_before_records_depth(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=200,
            score_before=_make_pov_score(mate=3),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        assert result.data["moves"][0]["missed_mate_depth"] == 3

    async def test_negative_mate_not_recorded(self):
        move = _move_eval(
            eval_before=-MATE_SCORE_ANALYSIS,
            eval_after=-200,
            score_before=_make_pov_score(mate=-5),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        assert result.data["moves"][0]["missed_mate_depth"] is None

    async def test_checkmate_delivered_no_missed_mate(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=100000,
            score_before=_make_pov_score(mate=1),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        # Checkmate was delivered — not a missed mate
        assert result.data["moves"][0]["missed_mate_depth"] is None
        assert result.data["moves"][0]["cp_loss"] == 0


class TestMateLostClassification:
    """Lichess-style MateLost: had winning mate → now just CP.

    Classification depends on eval_after:
      > 999 → inaccuracy (still crushing)
      > 700 → mistake
      else  → blunder
    """

    async def test_mate_lost_to_bad_position_is_blunder(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=-100,
            score_before=_make_pov_score(mate=2),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("blunder")
        assert m["missed_mate_depth"] == 2

    async def test_mate_lost_still_crushing_is_inaccuracy(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=1200,
            score_before=_make_pov_score(mate=3),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("inaccuracy")

    async def test_mate_lost_still_winning_is_mistake(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=800,
            score_before=_make_pov_score(mate=5),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("mistake")

    async def test_mate_lost_to_equal_is_blunder(self):
        move = _move_eval(
            eval_before=MATE_SCORE_ANALYSIS,
            eval_after=50,
            score_before=_make_pov_score(mate=2),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("blunder")


class TestFilteringWithMateDepth:
    def test_short_mate_miss_always_valid(self):
        blunder = {
            "eval_before": MATE_SCORE_ANALYSIS,
            "eval_after": 600,
            "missed_mate_depth": 2,
        }
        assert is_valid_blunder(blunder)

    def test_long_mate_miss_filtered_if_still_winning(self):
        blunder = {
            "eval_before": MATE_SCORE_ANALYSIS,
            "eval_after": 600,
            "missed_mate_depth": 10,
        }
        # missed_mate_depth > threshold, so the short-mate bypass doesn't apply,
        # and eval_after >= STILL_WINNING_THRESHOLD filters it out
        assert not is_valid_blunder(blunder)

    def test_no_mate_depth_uses_standard_rules(self):
        blunder = {"eval_before": 200, "eval_after": -100, "missed_mate_depth": None}
        assert is_valid_blunder(blunder)

    def test_mate_at_threshold_is_valid(self):
        blunder = {
            "eval_before": MATE_SCORE_ANALYSIS,
            "eval_after": 600,
            "missed_mate_depth": LONG_MATE_DEPTH_THRESHOLD,
        }
        assert is_valid_blunder(blunder)


class TestTrainerWeightsWithMateDepth:
    @pytest.fixture
    def trainer(self):
        return Trainer(
            games=MagicMock(),
            attempts=MagicMock(),
            analysis=MagicMock(),
        )

    def _blunder(self, missed_mate_depth: int | None = None) -> dict:
        return {
            "game_id": "g1",
            "ply": 10,
            "player": 0,
            "uci": "e2e4",
            "san": "e4",
            "eval_before": 50,
            "eval_after": -200,
            "cp_loss": 300,
            "tactical_pattern": None,
            "difficulty": None,
            "missed_mate_depth": missed_mate_depth,
        }

    async def test_mate_in_1_gets_highest_boost(self, trainer):
        candidates = [
            self._blunder(missed_mate_depth=1),
            self._blunder(missed_mate_depth=None),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert weights[0] == pytest.approx(2.0)
        assert weights[1] == pytest.approx(1.0)

    async def test_mate_in_4_gets_moderate_boost(self, trainer):
        candidates = [
            self._blunder(missed_mate_depth=4),
            self._blunder(missed_mate_depth=None),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert weights[0] == pytest.approx(1.5)
        assert weights[1] == pytest.approx(1.0)

    async def test_long_mate_no_boost(self, trainer):
        candidates = [
            self._blunder(missed_mate_depth=10),
            self._blunder(missed_mate_depth=None),
        ]
        trainer.attempts.get_failure_rates_by_pattern = AsyncMock(return_value={})
        weights = await trainer._compute_weights(candidates)
        assert weights[0] == weights[1]
