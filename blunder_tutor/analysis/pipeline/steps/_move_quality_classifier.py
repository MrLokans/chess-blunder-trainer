"""Move-quality classification helpers used by MoveQualityStep.

Lives as a sibling private module so the step class stays focused on the
step-protocol surface; classification rules + dataclass live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import chess
import chess.engine

from blunder_tutor.analysis.thresholds import winning_chances
from blunder_tutor.constants import MATE_SCORE_ANALYSIS, MATE_THRESHOLD, MAX_CP_LOSS

if TYPE_CHECKING:
    from blunder_tutor.analysis.thresholds import Thresholds


# Move-quality classification labels. Match `CLASSIFICATION_LABELS` in
# constants.py but referenced here by a private alias because this module
# also uses "good" — a label that exists at the wire level but not in the
# DB-backed `CLASSIFICATION_*` integer constants (good = 0).
_LABEL_GOOD = "good"
_LABEL_INACCURACY = "inaccuracy"
_LABEL_MISTAKE = "mistake"
_LABEL_BLUNDER = "blunder"

_LABEL_TO_INT = MappingProxyType(
    {_LABEL_GOOD: 0, _LABEL_INACCURACY: 1, _LABEL_MISTAKE: 2, _LABEL_BLUNDER: 3}
)

# Mate-transition thresholds (from Lichess Advice.scala).
_MATE_CP_INACCURACY = -999
_MATE_CP_MISTAKE = -700


@dataclass(frozen=True, slots=True)
class MoveClassification:
    label: str
    delta: int
    cp_loss: int
    missed_mate_depth: int | None


def class_to_int(label: str) -> int:
    return _LABEL_TO_INT[label]


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


def _pick_label(
    mate_before: int | None,
    eval_before: int,
    eval_after: int,
    thresholds: Thresholds,
) -> str:
    is_mate_before = mate_before is not None
    has_winning_before = is_mate_before and mate_before > 0
    is_mate_after = abs(eval_after) >= MATE_THRESHOLD
    has_winning_after = is_mate_after and eval_after > 0
    has_losing_after = is_mate_after and eval_after < 0

    if not is_mate_before and has_losing_after:  # mate_created
        return _classify_mate_created(eval_before)
    if has_winning_before and not has_winning_after and not has_losing_after:
        return _classify_mate_lost(eval_after)
    if has_winning_before and has_losing_after:  # mate_delayed
        return _LABEL_BLUNDER

    return _classify_wc(
        max(0.0, winning_chances(eval_before) - winning_chances(eval_after)),
        thresholds,
    )


def classify_move(
    move_data: dict[str, Any], thresholds: Thresholds
) -> MoveClassification:
    eval_before = move_data["eval_before"]
    eval_after = move_data["eval_after"]

    if eval_after == MATE_SCORE_ANALYSIS:  # Checkmate delivered
        return MoveClassification(
            label=_LABEL_GOOD, delta=0, cp_loss=0, missed_mate_depth=None
        )

    delta = eval_before - eval_after
    cp_loss = min(max(0, delta), MAX_CP_LOSS)

    player = chess.WHITE if move_data["player"] == "white" else chess.BLACK
    mate_before = _get_mate_depth(move_data["info_before"]["score"], player)
    label = _pick_label(mate_before, eval_before, eval_after, thresholds)

    return MoveClassification(
        label=label,
        delta=delta,
        cp_loss=cp_loss,
        missed_mate_depth=(
            mate_before if mate_before is not None and mate_before > 0 else None
        ),
    )


def build_move_record(
    move_data: dict[str, Any],
    classification: MoveClassification,
    difficulty: int | None,
) -> dict[str, Any]:
    return {
        "ply": move_data["ply"],
        "move_number": move_data["move_number"],
        "player": move_data["player"],
        "uci": move_data["uci"],
        "san": move_data["san"],
        "eval_before": move_data["eval_before"],
        "eval_after": move_data["eval_after"],
        "delta": classification.delta,
        "cp_loss": classification.cp_loss,
        "classification": class_to_int(classification.label),
        "best_move_uci": move_data["best_move_uci"],
        "best_move_san": move_data["best_move_san"],
        "best_line": move_data["best_line"],
        "best_move_eval": move_data["best_move_eval"],
        "difficulty": difficulty,
        "missed_mate_depth": classification.missed_mate_depth,
    }
