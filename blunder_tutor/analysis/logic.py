from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tqdm import tqdm

from blunder_tutor.analysis.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelineExecutor,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.analysis.thresholds import Thresholds

if TYPE_CHECKING:
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository


# Re-export for backward compatibility
__all__ = ["GameAnalyzer", "Thresholds"]


class GameAnalyzer:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        games_repo: GameRepository,
        engine_path: str,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.games_repo = games_repo
        self.engine_path = engine_path
        self._log = logging.getLogger("GameAnalyzer")
        self._executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=games_repo,
            engine_path=engine_path,
        )

    async def analyze_game(
        self,
        game_id: str,
        depth: int | None = 14,
        time_limit: float | None = None,
        thresholds: Thresholds | None = None,
        steps: list[str] | None = None,
        force_rerun: bool = False,
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
        )

        if not report.success:
            raise RuntimeError(f"Pipeline failed: {report.error}")

    async def analyze_bulk(
        self,
        depth: int | None = 14,
        time_limit: float | None = None,
        source: str | None = None,
        username: str | None = None,
        limit: int | None = None,
        force: bool = False,
        steps: list[str] | None = None,
    ) -> dict[str, int]:
        processed = 0
        skipped = 0
        analyzed = 0

        game_ids = await self.games_repo.list_unanalyzed_game_ids(source, username)
        if limit is not None:
            game_ids = game_ids[:limit]

        self._log.info("Processing %d games", len(game_ids))
        with tqdm(total=len(game_ids), desc="Analyze games", unit="game") as progress:
            for game_id in game_ids:
                if await self.analysis_repo.analysis_exists(game_id) and not force:
                    skipped += 1
                    processed += 1
                    progress.update(1)
                    continue
                await self.analyze_game(
                    game_id=game_id,
                    depth=depth,
                    time_limit=time_limit,
                    steps=steps,
                    force_rerun=force,
                )
                analyzed += 1
                processed += 1
                progress.update(1)

        return {"processed": processed, "analyzed": analyzed, "skipped": skipped}
