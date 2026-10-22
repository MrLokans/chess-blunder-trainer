from __future__ import annotations

import math

from blunder_tutor.analysis.thresholds import winning_chances

# `a * exp(-b * win_drop) - c` clamped to [0, 100]; coefficients are Lichess's empirical
# fit (AccuracyPercent.scala), defined over the drop in win percentage, not centipawns.
_ACCURACY_COEFF_A = 103.1668
_ACCURACY_COEFF_B = 0.04354
_ACCURACY_COEFF_C = 3.1668
_WIN_PERCENT_SCALE = 50.0

type MoveEvals = tuple[int, int]


def win_percent_drop(eval_before: int, eval_after: int) -> float:
    """Both evals from the mover's side; win% = 50 + 50 * winning_chances."""
    drop = winning_chances(eval_before) - winning_chances(eval_after)
    return max(0.0, _WIN_PERCENT_SCALE * drop)


def move_accuracy(win_drop: float) -> float:
    if win_drop <= 0:
        return 100.0
    return max(
        0.0,
        _ACCURACY_COEFF_A * math.exp(-_ACCURACY_COEFF_B * win_drop) - _ACCURACY_COEFF_C,
    )


def game_accuracy(moves: list[MoveEvals]) -> float:
    if not moves:
        return 0.0
    accuracies = [move_accuracy(win_percent_drop(*move)) for move in moves]
    return sum(accuracies) / len(accuracies)
