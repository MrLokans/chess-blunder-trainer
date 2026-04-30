from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import chess

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps._move_quality_classifier import (
    build_move_record,
    class_to_int,
    classify_move,
)
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext

# Difficulty heuristic constants. Each move's "difficulty" score (0-100)
# rewards positions that are objectively harder to navigate: quiet best
# moves, narrow legal-move counts, and deep tactics. Scoring weights are
# tuned by manual review of analyzed games.
DIFFICULTY_NO_BEST_MOVE_DEFAULT = 50
DIFFICULTY_QUIET_BEST = 40
DIFFICULTY_CAPTURE_NO_CHECK = 15
DIFFICULTY_FORCED_BEST = 5
DIFFICULTY_VERY_NARROW = 30  # legal_count ≤ 3
DIFFICULTY_NARROW = 20  # legal_count ≤ 8
DIFFICULTY_MODERATE = 10  # legal_count ≤ 15
DIFFICULTY_DEEP_TACTIC_THRESHOLD_CP = 400
DIFFICULTY_DEEP_TACTIC_BONUS = 15
LEGAL_COUNT_VERY_NARROW = 3
LEGAL_COUNT_NARROW = 8
LEGAL_COUNT_MODERATE = 15

# (is_capture, gives_check) → difficulty score for the best move's
# "quietness". Quiet (non-forcing) best moves are harder to spot than
# captures or checks; checks dominate captures.
_QUIETNESS_SCORES = MappingProxyType(
    {
        (False, False): DIFFICULTY_QUIET_BEST,
        (True, False): DIFFICULTY_CAPTURE_NO_CHECK,
        (False, True): DIFFICULTY_FORCED_BEST,
        (True, True): DIFFICULTY_FORCED_BEST,
    }
)


def _score_narrowness(legal_count: int) -> int:
    if legal_count <= LEGAL_COUNT_VERY_NARROW:
        return DIFFICULTY_VERY_NARROW
    if legal_count <= LEGAL_COUNT_NARROW:
        return DIFFICULTY_NARROW
    if legal_count <= LEGAL_COUNT_MODERATE:
        return DIFFICULTY_MODERATE
    return 0


def compute_difficulty(
    board: chess.Board,
    best_move_uci: str | None,
    cp_loss: int,
    classification: int,
) -> int:
    if classification < class_to_int("inaccuracy"):
        return 0

    if not best_move_uci:
        return DIFFICULTY_NO_BEST_MOVE_DEFAULT

    try:
        best_move = chess.Move.from_uci(best_move_uci)
    except ValueError:
        return DIFFICULTY_NO_BEST_MOVE_DEFAULT

    is_capture = board.is_capture(best_move)
    gives_check = board.gives_check(best_move)

    score = _QUIETNESS_SCORES[(is_capture, gives_check)]
    score += _score_narrowness(board.legal_moves.count())

    # Very large cp_loss with a quiet best move suggests a deep tactic
    if (
        cp_loss >= DIFFICULTY_DEEP_TACTIC_THRESHOLD_CP
        and not is_capture
        and not gives_check
    ):
        score += DIFFICULTY_DEEP_TACTIC_BONUS

    return min(score, 100)


def _difficulty_for(
    move_data: dict[str, Any], cp_loss: int, classification: int
) -> int | None:
    board = move_data.get("board")
    if board is None:
        return None
    return compute_difficulty(
        board, move_data["best_move_uci"], cp_loss, classification
    )


class MoveQualityStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "move_quality"

    @property
    def depends_on(self) -> frozenset[str]:
        return frozenset(("stockfish",))

    async def execute(self, ctx: StepContext) -> StepResult:
        stockfish_result = ctx.get_step_result("stockfish")
        if not stockfish_result or not stockfish_result.success:
            return StepResult(
                step_id=self.step_id,
                success=False,
                error="Stockfish step not completed",
            )

        moves = [
            build_move_record(
                move_data,
                classification := classify_move(move_data, ctx.thresholds),
                _difficulty_for(
                    move_data,
                    classification.cp_loss,
                    class_to_int(classification.label),
                ),
            )
            for move_data in stockfish_result.data.get("move_evals", [])
        ]

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"moves": moves, "analyzed_at": datetime.now(UTC).isoformat()},
        )
