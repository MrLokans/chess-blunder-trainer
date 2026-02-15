"""Shared helpers for pipeline step tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import chess

from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.thresholds import Thresholds
from blunder_tutor.constants import MATE_SCORE_ANALYSIS


def make_pov_score(cp: int | None = None, mate: int | None = None) -> MagicMock:
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


def make_move_eval(
    *,
    eval_before: int,
    eval_after: int,
    score_before: MagicMock | None = None,
    ply: int = 1,
) -> dict:
    if score_before is None:
        score_before = make_pov_score(cp=eval_before)
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


def make_mock_context(move_evals: list[dict]) -> StepContext:
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
