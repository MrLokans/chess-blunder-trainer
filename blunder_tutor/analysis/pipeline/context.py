from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import chess.engine
import chess.pgn

if TYPE_CHECKING:
    from blunder_tutor.analysis.thresholds import Thresholds
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


@dataclass
class StepResult:
    step_id: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class StepContext:
    game_id: str
    game: chess.pgn.Game
    analysis_repo: AnalysisRepository
    game_repo: GameRepository
    engine_path: str
    thresholds: Thresholds
    depth: int | None = 14
    time_limit: float | None = None
    step_results: dict[str, StepResult] = field(default_factory=dict)
    force_rerun: bool = False
    engine: chess.engine.UciProtocol | None = None

    def get_step_result(self, step_id: str) -> StepResult | None:
        return self.step_results.get(step_id)

    def add_step_result(self, result: StepResult) -> None:
        self.step_results[result.step_id] = result
