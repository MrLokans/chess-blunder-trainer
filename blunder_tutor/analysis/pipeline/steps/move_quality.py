from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.analysis.thresholds import winning_chances
from blunder_tutor.constants import (
    MATE_SCORE_ANALYSIS,
    MATE_THRESHOLD,
    MAX_CP_LOSS,
)

# Move-quality classification labels. Match `CLASSIFICATION_LABELS` in
# constants.py but referenced here by a private alias because this module
# also uses "good" — a label that exists at the wire level but not in the
# DB-backed `CLASSIFICATION_*` integer constants (good = 0).
_LABEL_GOOD = "good"
_LABEL_INACCURACY = "inaccuracy"
_LABEL_MISTAKE = "mistake"
_LABEL_BLUNDER = "blunder"

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

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext
    from blunder_tutor.analysis.thresholds import Thresholds


def _is_mate_score(score: chess.engine.PovScore, side: chess.Color) -> bool:
    pov = score.pov(side)
    return pov.is_mate()


def _get_mate_depth(score: chess.engine.PovScore, side: chess.Color) -> int | None:
    pov = score.pov(side)
    return pov.mate() if pov.is_mate() else None


def _classify_wc(wc_loss: float, thresholds: Thresholds) -> str:
    if wc_loss >= thresholds.wc_blunder:
        return _LABEL_BLUNDER
    if wc_loss >= thresholds.wc_mistake:
        return _LABEL_MISTAKE
    if wc_loss >= thresholds.wc_inaccuracy:
        return _LABEL_INACCURACY
    return _LABEL_GOOD


# Mate-transition thresholds (from Lichess Advice.scala).
_MATE_CP_INACCURACY = -999
_MATE_CP_MISTAKE = -700


def _classify_mate_created(prev_pov_cp: int) -> str:
    if prev_pov_cp < _MATE_CP_INACCURACY:
        return _LABEL_INACCURACY
    if prev_pov_cp < _MATE_CP_MISTAKE:
        return _LABEL_MISTAKE
    return _LABEL_BLUNDER


def _classify_mate_lost(current_pov_cp: int) -> str:
    if current_pov_cp > -_MATE_CP_INACCURACY:
        return _LABEL_INACCURACY
    if current_pov_cp > -_MATE_CP_MISTAKE:
        return _LABEL_MISTAKE
    return _LABEL_BLUNDER


_LABEL_TO_INT = MappingProxyType(
    {_LABEL_GOOD: 0, _LABEL_INACCURACY: 1, _LABEL_MISTAKE: 2, _LABEL_BLUNDER: 3}
)


def _class_to_int(label: str) -> int:
    return _LABEL_TO_INT[label]


def compute_difficulty(
    board: chess.Board,
    best_move_uci: str | None,
    cp_loss: int,
    classification: int,
) -> int:
    if classification < _class_to_int(_LABEL_INACCURACY):
        return 0

    if not best_move_uci:
        return DIFFICULTY_NO_BEST_MOVE_DEFAULT

    try:
        best_move = chess.Move.from_uci(best_move_uci)
    except ValueError:
        return DIFFICULTY_NO_BEST_MOVE_DEFAULT

    score = 0

    # Quiet (non-forcing) best moves are harder to find
    is_capture = board.is_capture(best_move)
    gives_check = board.gives_check(best_move)
    if not is_capture and not gives_check:
        score += DIFFICULTY_QUIET_BEST
    elif is_capture and not gives_check:
        score += DIFFICULTY_CAPTURE_NO_CHECK
    else:
        score += DIFFICULTY_FORCED_BEST

    # Fewer safe alternatives → harder position (less choice = more forgivable)
    legal_count = board.legal_moves.count()
    if legal_count <= LEGAL_COUNT_VERY_NARROW:
        score += DIFFICULTY_VERY_NARROW
    elif legal_count <= LEGAL_COUNT_NARROW:
        score += DIFFICULTY_NARROW
    elif legal_count <= LEGAL_COUNT_MODERATE:
        score += DIFFICULTY_MODERATE

    # Very large cp_loss with a quiet best move suggests a deep tactic
    if (
        cp_loss >= DIFFICULTY_DEEP_TACTIC_THRESHOLD_CP
        and not is_capture
        and not gives_check
    ):
        score += DIFFICULTY_DEEP_TACTIC_BONUS

    return min(score, 100)


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

        move_evals = stockfish_result.data.get("move_evals", [])
        thresholds = ctx.thresholds

        moves: list[dict] = []
        for move_data in move_evals:
            eval_before = move_data["eval_before"]
            eval_after = move_data["eval_after"]
            info_before = move_data["info_before"]
            player = chess.WHITE if move_data["player"] == "white" else chess.BLACK

            missed_mate_depth: int | None = None

            if eval_after == MATE_SCORE_ANALYSIS:  # Checkmate delivered
                delta = 0
                cp_loss = 0
                class_label = _LABEL_GOOD
            else:
                delta = eval_before - eval_after
                cp_loss = min(max(0, delta), MAX_CP_LOSS)

                mate_before = _get_mate_depth(info_before["score"], player)
                has_winning_mate_before = mate_before is not None and mate_before > 0
                is_mate_before = mate_before is not None

                # Detect mate-after from eval (score_to_cp uses mate_score=MATE_SCORE_ANALYSIS)
                is_mate_after = abs(eval_after) >= MATE_THRESHOLD
                has_winning_mate_after = is_mate_after and eval_after > 0
                has_losing_mate_after = is_mate_after and eval_after < 0

                if has_winning_mate_before:
                    missed_mate_depth = mate_before

                # Mate transition types (Lichess Advice.scala)
                mate_created = not is_mate_before and has_losing_mate_after
                mate_lost = (
                    has_winning_mate_before
                    and not has_winning_mate_after
                    and not has_losing_mate_after
                )
                mate_delayed = has_winning_mate_before and has_losing_mate_after

                if mate_created:
                    class_label = _classify_mate_created(eval_before)
                elif mate_lost:
                    class_label = _classify_mate_lost(eval_after)
                elif mate_delayed:
                    class_label = _LABEL_BLUNDER
                else:
                    wc_before = winning_chances(eval_before)
                    wc_after = winning_chances(eval_after)
                    wc_loss = max(0.0, wc_before - wc_after)
                    class_label = _classify_wc(wc_loss, thresholds)

            classification = _class_to_int(class_label)
            board = move_data.get("board")
            difficulty = (
                compute_difficulty(
                    board, move_data["best_move_uci"], cp_loss, classification
                )
                if board is not None
                else None
            )

            moves.append(
                {
                    "ply": move_data["ply"],
                    "move_number": move_data["move_number"],
                    "player": move_data["player"],
                    "uci": move_data["uci"],
                    "san": move_data["san"],
                    "eval_before": eval_before,
                    "eval_after": eval_after,
                    "delta": delta,
                    "cp_loss": cp_loss,
                    "classification": classification,
                    "best_move_uci": move_data["best_move_uci"],
                    "best_move_san": move_data["best_move_san"],
                    "best_line": move_data["best_line"],
                    "best_move_eval": move_data["best_move_eval"],
                    "difficulty": difficulty,
                    "missed_mate_depth": missed_mate_depth,
                }
            )

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"moves": moves, "analyzed_at": datetime.now(UTC).isoformat()},
        )
