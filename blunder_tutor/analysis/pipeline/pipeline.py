from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep


class PipelinePreset(Enum):
    FULL = ["eco", "stockfish", "move_quality", "phase", "write"]
    FAST = ["eco", "phase"]
    BACKFILL_ECO = ["eco"]
    BACKFILL_PHASE = ["phase"]


@dataclass
class PipelineConfig:
    steps: list[str] = field(default_factory=lambda: PipelinePreset.FULL.value.copy())
    force_rerun: bool = False

    @classmethod
    def from_preset(
        cls, preset: PipelinePreset, force_rerun: bool = False
    ) -> PipelineConfig:
        return cls(steps=preset.value.copy(), force_rerun=force_rerun)


class AnalysisPipeline:
    def __init__(
        self,
        config: PipelineConfig,
        available_steps: list[AnalysisStep],
    ) -> None:
        self.config = config
        self._steps_by_id = {step.step_id: step for step in available_steps}
        self._validate_steps()

    def _validate_steps(self) -> None:
        for step_id in self.config.steps:
            if step_id not in self._steps_by_id:
                available = list(self._steps_by_id.keys())
                raise ValueError(f"Unknown step '{step_id}'. Available: {available}")

    @classmethod
    def from_preset(
        cls,
        preset: PipelinePreset,
        available_steps: list[AnalysisStep],
        force_rerun: bool = False,
    ) -> AnalysisPipeline:
        config = PipelineConfig.from_preset(preset, force_rerun)
        return cls(config, available_steps)

    def get_ordered_steps(self) -> list[AnalysisStep]:
        requested_ids = set(self.config.steps)

        for step_id in self.config.steps:
            step = self._steps_by_id[step_id]
            missing_deps = step.depends_on - requested_ids
            if missing_deps:
                for dep_id in missing_deps:
                    if dep_id in self._steps_by_id and dep_id not in requested_ids:
                        requested_ids.add(dep_id)

        return self._topological_sort(requested_ids)

    def _topological_sort(self, step_ids: set[str]) -> list[AnalysisStep]:
        visited: set[str] = set()
        result: list[AnalysisStep] = []

        def visit(step_id: str) -> None:
            if step_id in visited:
                return
            if step_id not in step_ids:
                return

            step = self._steps_by_id.get(step_id)
            if step is None:
                return

            for dep_id in step.depends_on:
                visit(dep_id)

            visited.add(step_id)
            result.append(step)

        for step_id in step_ids:
            visit(step_id)

        return result
