from __future__ import annotations

from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.analysis.pipeline.steps.eco import ECOClassifyStep
from blunder_tutor.analysis.pipeline.steps.move_quality import MoveQualityStep
from blunder_tutor.analysis.pipeline.steps.phase import PhaseClassifyStep
from blunder_tutor.analysis.pipeline.steps.stockfish import StockfishAnalysisStep
from blunder_tutor.analysis.pipeline.steps.tactics import TacticsClassifyStep
from blunder_tutor.analysis.pipeline.steps.traps import TrapDetectionStep
from blunder_tutor.analysis.pipeline.steps.write import WriteAnalysisStep


def get_all_steps() -> list[AnalysisStep]:
    return [
        ECOClassifyStep(),
        StockfishAnalysisStep(),
        MoveQualityStep(),
        PhaseClassifyStep(),
        TacticsClassifyStep(),
        TrapDetectionStep(),
        WriteAnalysisStep(),
    ]
