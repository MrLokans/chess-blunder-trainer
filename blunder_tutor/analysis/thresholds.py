from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    inaccuracy: int = 50
    mistake: int = 100
    blunder: int = 200
