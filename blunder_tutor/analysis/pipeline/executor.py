from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import chess.engine

from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.thresholds import Thresholds

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.pipeline import AnalysisPipeline
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


@dataclass
class PipelineReport:
    game_id: str
    steps_executed: list[str] = field(default_factory=list)
    steps_skipped: list[str] = field(default_factory=list)
    steps_failed: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    success: bool = True
    error: str | None = None


class PipelineExecutor:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
        engine_path: str,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.game_repo = game_repo
        self.engine_path = engine_path
        self._log = logging.getLogger("PipelineExecutor")

    async def execute_pipeline(
        self,
        pipeline: AnalysisPipeline,
        game_id: str,
        thresholds: Thresholds | None = None,
        depth: int | None = 14,
        time_limit: float | None = None,
        engine: chess.engine.UciProtocol | None = None,
    ) -> PipelineReport:
        report = PipelineReport(
            game_id=game_id,
            started_at=datetime.now(UTC).isoformat(),
        )
        thresholds = thresholds or Thresholds()

        try:
            game = await self.game_repo.load_game(game_id)
        except Exception as e:
            report.success = False
            report.error = f"Failed to load game: {e}"
            report.completed_at = datetime.now(UTC).isoformat()
            return report

        ctx = StepContext(
            game_id=game_id,
            game=game,
            analysis_repo=self.analysis_repo,
            game_repo=self.game_repo,
            engine_path=self.engine_path,
            thresholds=thresholds,
            depth=depth,
            time_limit=time_limit,
            force_rerun=pipeline.config.force_rerun,
            engine=engine,
        )

        ordered_steps = pipeline.get_ordered_steps()

        for step in ordered_steps:
            if not ctx.force_rerun and await step.is_completed(ctx):
                self._log.debug("Step %s already completed, skipping", step.step_id)
                report.steps_skipped.append(step.step_id)
                ctx.add_step_result(
                    StepResult(step_id=step.step_id, success=True, data={})
                )
                continue

            missing_deps = self._check_dependencies(step, ctx)
            if missing_deps:
                self._log.warning(
                    "Step %s missing dependencies: %s", step.step_id, missing_deps
                )
                report.steps_failed.append(step.step_id)
                report.success = False
                report.error = (
                    f"Step {step.step_id} missing dependencies: {missing_deps}"
                )
                break

            try:
                self._log.debug("Executing step %s", step.step_id)
                result = await step.execute(ctx)
                ctx.add_step_result(result)

                if result.success:
                    report.steps_executed.append(step.step_id)
                    await self.analysis_repo.mark_step_completed(game_id, step.step_id)
                else:
                    report.steps_failed.append(step.step_id)
                    report.success = False
                    report.error = result.error
                    break

            except Exception as e:
                self._log.exception("Step %s failed with exception", step.step_id)
                report.steps_failed.append(step.step_id)
                report.success = False
                report.error = str(e)
                break

        report.completed_at = datetime.now(UTC).isoformat()
        return report

    def _check_dependencies(self, step, ctx: StepContext) -> list[str]:
        missing = []
        for dep_id in step.depends_on:
            if dep_id not in ctx.step_results:
                missing.append(dep_id)
        return missing
