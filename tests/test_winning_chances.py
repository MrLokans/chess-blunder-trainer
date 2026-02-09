from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import chess
import pytest

from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.pipeline.steps.move_quality import (
    MoveQualityStep,
    _class_to_int,
    _classify_wc,
)
from blunder_tutor.analysis.thresholds import Thresholds, winning_chances
from blunder_tutor.constants import MATE_SCORE_ANALYSIS


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


class TestWinningChances:
    def test_equal_position(self):
        assert winning_chances(0) == pytest.approx(0.0)

    def test_positive_advantage(self):
        wc = winning_chances(200)
        assert 0.3 < wc < 0.4

    def test_large_advantage_saturates(self):
        wc = winning_chances(1000)
        assert wc > 0.9

    def test_mate_score_clamped_to_ceiling(self):
        wc_mate = winning_chances(100_000)
        wc_ceiling = winning_chances(1000)
        assert wc_mate == pytest.approx(wc_ceiling)
        assert wc_mate == pytest.approx(-winning_chances(-100_000))

    def test_symmetry(self):
        assert winning_chances(300) == pytest.approx(-winning_chances(-300))


class TestClassifyWc:
    def test_small_loss_is_good(self):
        assert _classify_wc(0.03, Thresholds()) == "good"

    def test_inaccuracy(self):
        assert _classify_wc(0.12, Thresholds()) == "inaccuracy"

    def test_mistake(self):
        assert _classify_wc(0.25, Thresholds()) == "mistake"

    def test_blunder(self):
        assert _classify_wc(0.35, Thresholds()) == "blunder"


class TestAlreadyLostPositionNotBlunder:
    async def test_losing_to_mate_not_blunder_when_already_lost(self):
        move = _move_eval(eval_before=-800, eval_after=-MATE_SCORE_ANALYSIS)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("mistake")

    async def test_losing_to_mate_is_blunder_from_decent_position(self):
        move = _move_eval(eval_before=-200, eval_after=-MATE_SCORE_ANALYSIS)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("blunder")

    async def test_equal_to_large_loss_is_blunder(self):
        move = _move_eval(eval_before=50, eval_after=-350)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("blunder")

    async def test_deeply_lost_to_slightly_more_lost_not_blunder(self):
        move = _move_eval(eval_before=-1000, eval_after=-MATE_SCORE_ANALYSIS)
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] <= _class_to_int("inaccuracy")

    async def test_within_mate_sequence_is_good(self):
        move = _move_eval(
            eval_before=-MATE_SCORE_ANALYSIS,
            eval_after=-MATE_SCORE_ANALYSIS,
            score_before=_make_pov_score(mate=-4),
        )
        ctx = _mock_context([move])
        step = MoveQualityStep()
        result = await step.execute(ctx)
        m = result.data["moves"][0]
        assert m["classification"] == _class_to_int("good")
