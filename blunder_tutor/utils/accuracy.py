from __future__ import annotations

import math

# Lichess-style move accuracy formula: a * exp(-b * cp_loss) - c, clamped
# to [0, 100]. Coefficients are empirical fits from Lichess's published
# Advice.scala — leaving them inline ties this implementation to a
# specific upstream reference.
_ACCURACY_COEFF_A = 103.1668
_ACCURACY_COEFF_B = 0.04354
_ACCURACY_COEFF_C = 3.1668


def move_accuracy(cp_loss: int) -> float:
    if cp_loss <= 0:
        return 100.0
    return max(
        0.0,
        _ACCURACY_COEFF_A * math.exp(-_ACCURACY_COEFF_B * cp_loss) - _ACCURACY_COEFF_C,
    )


def game_accuracy(cp_losses: list[int]) -> float:
    if not cp_losses:
        return 0.0
    return sum(move_accuracy(cp) for cp in cp_losses) / len(cp_losses)
