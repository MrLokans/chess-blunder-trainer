from __future__ import annotations

import math


def move_accuracy(cp_loss: int) -> float:
    if cp_loss <= 0:
        return 100.0
    return max(0.0, 103.1668 * math.exp(-0.04354 * cp_loss) - 3.1668)


def game_accuracy(cp_losses: list[int]) -> float:
    if not cp_losses:
        return 0.0
    return sum(move_accuracy(cp) for cp in cp_losses) / len(cp_losses)
