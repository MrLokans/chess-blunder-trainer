from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.analysis.logic import DEFAULT_CONCURRENCY
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.events.event_types import EventType

if TYPE_CHECKING:
    import chess.engine

    from blunder_tutor.analysis.engine_pool import WorkCoordinator
    from blunder_tutor.analysis.logic import GameAnalyzer
    from blunder_tutor.events.event_bus import EventBus
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class AnalyzeGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "analyze"

    def __init__(
        self,
        job_service: JobService,
        game_repo: GameRepository,
        analysis_repo: AnalysisRepository,
        analyzer: GameAnalyzer,
        event_bus: EventBus | None = None,
        coordinator: WorkCoordinator | None = None,
    ) -> None:
        self.job_service = job_service
        self.game_repo = game_repo
        self.analysis_repo = analysis_repo
        self.analyzer = analyzer
        self._event_bus = event_bus
        self._coordinator = coordinator

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        game_ids = kwargs.get("game_ids")
        source = kwargs.get("source")
        username = kwargs.get("username")
        steps = kwargs.get("steps")
        concurrency = kwargs.get("concurrency", DEFAULT_CONCURRENCY)

        if game_ids is None:
            game_ids = await self.game_repo.list_unanalyzed_game_ids(source, username)

        if not game_ids:
            await self.job_service.complete_job(job_id, {"analyzed": 0, "skipped": 0})
            return {"analyzed": 0, "skipped": 0}

        return await self._analyze_games(job_id, game_ids, steps, concurrency)

    async def _watch_cancellation(self, job_id: str, cancelled: asyncio.Event) -> None:
        if self._event_bus is None:
            return
        queue = await self._event_bus.subscribe(EventType.JOB_STATUS_CHANGED)
        try:
            while not cancelled.is_set():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    continue
                data = event.data
                if data.get("job_id") == job_id and data.get("status") == "failed":
                    cancelled.set()
                    return
        finally:
            await self._event_bus.unsubscribe(queue, EventType.JOB_STATUS_CHANGED)

    async def _analyze_games(
        self,
        job_id: str,
        game_ids: list[str],
        steps: list[str] | None = None,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> dict[str, Any]:
        from blunder_tutor.analysis.engine_pool import WorkCoordinator

        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, len(game_ids))

        owns_coordinator = self._coordinator is None
        coordinator = self._coordinator or WorkCoordinator(
            self.analyzer.engine_path, concurrency
        )
        if owns_coordinator:
            await coordinator.start()

        results = {"analyzed": 0, "skipped": 0, "failed": 0}
        processed = 0
        cancelled = asyncio.Event()
        watcher_task = asyncio.create_task(self._watch_cancellation(job_id, cancelled))

        try:
            logger.info(
                f"Starting parallel analysis of {len(game_ids)} games "
                f"with concurrency={concurrency}"
            )

            for game_id in game_ids:

                async def process_game(
                    engine: chess.engine.UciProtocol,
                    *,
                    _gid: str = game_id,
                ) -> None:
                    nonlocal processed

                    if cancelled.is_set():
                        return

                    if await self.analysis_repo.analysis_exists(_gid):
                        results["skipped"] += 1
                        processed += 1
                        await self.job_service.update_job_progress(
                            job_id, processed, len(game_ids)
                        )
                        return

                    try:
                        await self.analyzer.analyze_game(
                            _gid, steps=steps, engine=engine
                        )
                        await self.game_repo.mark_game_analyzed(_gid)

                        results["analyzed"] += 1
                        processed += 1
                        await self.job_service.update_job_progress(
                            job_id, processed, len(game_ids)
                        )
                    except Exception as e:
                        logger.error(f"Failed to analyze game {_gid}: {e}")
                        results["failed"] += 1
                        processed += 1
                        await self.job_service.update_job_progress(
                            job_id, processed, len(game_ids)
                        )

                coordinator.submit(process_game)

            await coordinator.drain()
            await self.job_service.complete_job(job_id, results)
            return results

        except asyncio.CancelledError:
            logger.info(f"Analysis job {job_id} cancelled, cleaning up...")
            raise

        except Exception as e:
            logger.error(f"Error in analysis job {job_id}: {e}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise

        finally:
            cancelled.set()
            watcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher_task
            if owns_coordinator:
                await coordinator.shutdown()
