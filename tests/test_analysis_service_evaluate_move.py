from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import chess
import chess.engine
import pytest

from blunder_tutor.services.analysis_service import AnalysisService

# Black to move after 1. e4.
BLACK_TO_MOVE = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def _service(score: chess.engine.PovScore) -> AnalysisService:
    coordinator = MagicMock()
    coordinator.submit = AsyncMock(return_value={"score": score})
    return AnalysisService(coordinator, chess.engine.Limit(depth=1))


@pytest.mark.parametrize(
    ("engine_score", "expected_cp", "expected_display"),
    [
        # The engine reports from the side to move (white) after black's move.
        (chess.engine.PovScore(chess.engine.Cp(-150), chess.WHITE), 150, "+1.5"),
        (chess.engine.PovScore(chess.engine.Mate(-2), chess.WHITE), 99998, "+M"),
    ],
)
async def test_black_move_is_scored_from_black_on_stored_scale(
    engine_score, expected_cp, expected_display
):
    evaluation = await _service(engine_score).evaluate_move(BLACK_TO_MOVE, "e7e5")

    assert evaluation.eval_cp == expected_cp
    assert evaluation.eval_display == expected_display
