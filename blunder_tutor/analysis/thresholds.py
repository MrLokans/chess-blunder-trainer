from __future__ import annotations

import math
from dataclasses import dataclass

# Lichess winning-chances coefficient and CP ceiling.
# https://github.com/lichess-org/scalachess — eval.scala, WinPercent
_WC_K = 0.00368208
_CP_CEILING = 1000


def winning_chances(cp: int) -> float:
    clamped = max(-_CP_CEILING, min(_CP_CEILING, cp))
    return 2.0 / (1.0 + math.exp(-_WC_K * clamped)) - 1.0


@dataclass(frozen=True)
class Thresholds:
    inaccuracy: int = 50
    mistake: int = 100
    blunder: int = 200

    wc_inaccuracy: float = 0.1
    wc_mistake: float = 0.2
    wc_blunder: float = 0.3
