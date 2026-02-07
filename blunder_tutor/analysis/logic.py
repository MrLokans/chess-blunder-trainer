from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import chess.engine
from tqdm import tqdm

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelineExecutor,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.analysis.thresholds import Thresholds
from blunder_tutor.constants import DEFAULT_ENGINE_CONCURRENCY

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


DEFAULT_CONCURRENCY = min(DEFAULT_ENGINE_CONCURRENCY, os.cpu_count() or 1)

__all__ = ["GameAnalyzer", "Thresholds"]


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
    ) -> None:
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

    async def analyze_bulk(
        self,
        depth: int | None = None,
        time_limit: float | None = None,
        source: str | None = None,
        username: str | None = None,
        limit: int | None = None,
        force: bool = False,
        steps: list[str] | None = None,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> dict[str, int]:
        game_ids = await self.games_repo.list_unanalyzed_game_ids(source, username)
        if limit is not None:
            game_ids = game_ids[:limit]

        if not game_ids:
            return {"processed": 0, "analyzed": 0, "skipped": 0}

        self._log.info(
            "Processing %d games with concurrency=%d", len(game_ids), concurrency
        )

        owns_coordinator = self._coordinator is None
        coordinator = self._coordinator or WorkCoordinator(
            self.engine_path, concurrency
        )
        if owns_coordinator:
            await coordinator.start()

        results = {"processed": 0, "analyzed": 0, "skipped": 0, "failed": 0}

        try:
            with tqdm(
                total=len(game_ids), desc="Analyze games", unit="game"
            ) as progress:
                for game_id in game_ids:

                    async def process_game(
                        engine: chess.engine.UciProtocol,
                        *,
                        _gid: str = game_id,
                    ) -> None:
                        skip = (
                            await self.analysis_repo.analysis_exists(_gid) and not force
                        )
                        if skip:
                            results["skipped"] += 1
                            results["processed"] += 1
                            progress.update(1)
                            return

                        try:
                            await self.analyze_game(
                                game_id=_gid,
                                depth=depth,
                                time_limit=time_limit,
                                steps=steps,
                                force_rerun=force,
                                engine=engine,
                            )
                            results["analyzed"] += 1
                            results["processed"] += 1
                            progress.update(1)
                        except Exception as e:
                            self._log.error("Failed to analyze game %s: %s", _gid, e)
                            results["failed"] += 1
                            results["processed"] += 1
                            progress.update(1)

                    coordinator.submit(process_game)

                await coordinator.drain()
        finally:
            if owns_coordinator:
                await coordinator.shutdown()

        return results
