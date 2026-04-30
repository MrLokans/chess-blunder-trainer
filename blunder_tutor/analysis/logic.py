from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import chess.engine
from tqdm import tqdm

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.pipeline.executor import PipelineExecutor, PipelineReport
from blunder_tutor.analysis.pipeline.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.analysis.thresholds import Thresholds
from blunder_tutor.constants import DEFAULT_CONCURRENCY

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


@dataclass(frozen=True)
class BulkAnalysisOptions:
    depth: int | None = None
    time_limit: float | None = None
    source: str | None = None
    username: str | None = None
    limit: int | None = None
    force: bool = False
    steps: list[str] | None = None
    concurrency: int = DEFAULT_CONCURRENCY


class GameAnalyzer:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        games_repo: GameRepository,
        engine_path: str,
        coordinator: WorkCoordinator | None = None,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.games_repo = games_repo
        self.engine_path = engine_path
        self._coordinator = coordinator
        self._log = logging.getLogger("GameAnalyzer")
        self._executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=games_repo,
            engine_path=engine_path,
        )

    async def analyze_game(
        self,
        game_id: str,
        depth: int | None = None,
        time_limit: float | None = None,
        thresholds: Thresholds | None = None,
        steps: list[str] | None = None,
        force_rerun: bool = False,
        engine: chess.engine.UciProtocol | None = None,
    ) -> PipelineReport:
        thresholds = thresholds or Thresholds()
        available_steps = get_all_steps()

        if steps is not None:
            config = PipelineConfig(steps=steps, force_rerun=force_rerun)
        else:
            config = PipelineConfig.from_preset(
                PipelinePreset.FULL, force_rerun=force_rerun
            )

        pipeline = AnalysisPipeline(config, available_steps)
        report = await self._executor.execute_pipeline(
            pipeline=pipeline,
            game_id=game_id,
            thresholds=thresholds,
            depth=depth,
            time_limit=time_limit,
            engine=engine,
        )

        if not report.success:
            raise RuntimeError(f"Pipeline failed: {report.error}")

        return report

    async def analyze_bulk(self, options: BulkAnalysisOptions) -> dict[str, int]:
        game_ids = await self.games_repo.list_unanalyzed_game_ids(
            options.source, options.username
        )
        if options.limit is not None:
            game_ids = game_ids[: options.limit]

        if not game_ids:
            return {"processed": 0, "analyzed": 0, "skipped": 0}  # noqa: WPS226 — counter dict keys repeated as we increment them per-game in the analyze loop.

        self._log.info(
            "Processing %d games with concurrency=%d",
            len(game_ids),
            options.concurrency,
        )

        owns_coordinator = self._coordinator is None
        coordinator = self._coordinator or WorkCoordinator(
            self.engine_path, options.concurrency
        )
        if owns_coordinator:
            await coordinator.start()

        results = {"processed": 0, "analyzed": 0, "skipped": 0, "failed": 0}

        try:  # noqa: WPS501 — conditional cleanup (`if owns_coordinator: shutdown`); not a single-resource context manager.
            await self._submit_all(coordinator, game_ids, options, results)
        finally:
            if owns_coordinator:
                await coordinator.shutdown()

        return results

    async def _submit_all(
        self,
        coordinator: WorkCoordinator,
        game_ids: list[str],
        options: BulkAnalysisOptions,
        results: dict[str, int],
    ) -> None:
        with tqdm(total=len(game_ids), desc="Analyze games", unit="game") as progress:
            for game_id in game_ids:
                coordinator.submit(
                    functools.partial(
                        self._process_one_game,
                        game_id=game_id,
                        options=options,
                        results=results,
                        progress=progress,
                    )
                )
            await coordinator.drain()

    async def _process_one_game(
        self,
        engine: chess.engine.UciProtocol,
        *,
        game_id: str,
        options: BulkAnalysisOptions,
        results: dict[str, int],
        progress: tqdm,
    ) -> None:
        already_analyzed = await self.analysis_repo.analysis_exists(game_id)
        if already_analyzed and not options.force:
            results["skipped"] += 1
            results["processed"] += 1
            progress.update(1)
            return

        try:  # noqa: WPS505 — per-game error isolation: a failure on one game must not abort the whole batch.
            await self.analyze_game(
                game_id=game_id,
                depth=options.depth,
                time_limit=options.time_limit,
                steps=options.steps,
                force_rerun=options.force,
                engine=engine,
            )
            results["analyzed"] += 1
        except Exception as exc:
            self._log.error("Failed to analyze game %s: %s", game_id, exc)
            results["failed"] += 1
        results["processed"] += 1
        progress.update(1)
