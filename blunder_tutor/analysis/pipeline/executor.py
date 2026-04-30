from __future__ import annotations

import logging
import time
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
    step_durations: dict[str, float] = field(default_factory=dict)
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
        depth: int | None = None,
        time_limit: float | None = None,
        engine: chess.engine.UciProtocol | None = None,
    ) -> PipelineReport:
        report = PipelineReport(
            game_id=game_id,
            started_at=datetime.now(UTC).isoformat(),
        )

        ctx = await self._load_game_or_report(
            game_id, report, thresholds, depth, time_limit, pipeline, engine
        )
        if ctx is None:
            return report

        for step in pipeline.get_ordered_steps():
            if not await self._run_single_step(step, ctx, report):
                break

        if report.steps_executed:
            await self.analysis_repo.mark_steps_completed(
                game_id, report.steps_executed
            )

        report.completed_at = datetime.now(UTC).isoformat()
        return report

    async def _load_game_or_report(
        self,
        game_id: str,
        report: PipelineReport,
        thresholds: Thresholds | None,
        depth: int | None,
        time_limit: float | None,
        pipeline: AnalysisPipeline,
        engine: chess.engine.UciProtocol | None,
    ) -> StepContext | None:
        try:
            game = await self.game_repo.load_game(game_id)
        except Exception as e:
            report.success = False
            report.error = f"Failed to load game: {e}"
            report.completed_at = datetime.now(UTC).isoformat()
            return None

        return StepContext(
            game_id=game_id,
            game=game,
            analysis_repo=self.analysis_repo,
            game_repo=self.game_repo,
            engine_path=self.engine_path,
            thresholds=thresholds or Thresholds(),
            depth=depth,
            time_limit=time_limit,
            force_rerun=pipeline.config.force_rerun,
            engine=engine,
        )

    async def _run_single_step(
        self, step, ctx: StepContext, report: PipelineReport
    ) -> bool:
        if not ctx.force_rerun and await step.is_completed(ctx):
            self._log.debug("Step %s already completed, skipping", step.step_id)
            report.steps_skipped.append(step.step_id)
            ctx.add_step_result(StepResult(step_id=step.step_id, success=True, data={}))
            return True

        missing_deps = self._check_dependencies(step, ctx)
        if missing_deps:
            self._log.warning(
                "Step %s missing dependencies: %s", step.step_id, missing_deps
            )
            report.steps_failed.append(step.step_id)
            report.success = False
            report.error = f"Step {step.step_id} missing dependencies: {missing_deps}"
            return False

        return await self._execute_step(step, ctx, report)

    async def _execute_step(
        self, step, ctx: StepContext, report: PipelineReport
    ) -> bool:
        self._log.debug("Executing step %s", step.step_id)
        t0 = time.perf_counter()
        try:
            result = await step.execute(ctx)
        except Exception as e:
            self._log.exception("Step %s failed with exception", step.step_id)
            report.steps_failed.append(step.step_id)
            report.success = False
            report.error = str(e)
            return False
        report.step_durations[step.step_id] = time.perf_counter() - t0
        ctx.add_step_result(result)

        if result.success:
            report.steps_executed.append(step.step_id)
            return True
        report.steps_failed.append(step.step_id)
        report.success = False
        report.error = result.error
        return False

    def _check_dependencies(self, step, ctx: StepContext) -> list[str]:
        return [dep_id for dep_id in step.depends_on if dep_id not in ctx.step_results]
