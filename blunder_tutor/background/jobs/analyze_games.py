from __future__ import annotations

import asyncio
import contextlib
import logging
from functools import partial
from typing import Any, ClassVar

import chess.engine

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.constants import DEFAULT_CONCURRENCY, JOB_STATUS_FAILED
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)


class _AnalyzeContext:
    """Mutable per-batch state shared between submitted analysis tasks."""

    def __init__(
        self,
        steps: list[str] | None,
        total: int,
        cancelled: asyncio.Event,
        progress: ProgressCallback,
    ) -> None:
        self.steps = steps
        self.total = total
        self.cancelled = cancelled
        self.progress = progress
        self.results = {"analyzed": 0, "skipped": 0, "failed": 0}
        self.processed = 0


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
        steps = kwargs.get("steps")
        concurrency = kwargs.get("concurrency", DEFAULT_CONCURRENCY)

        if game_ids is None:
            game_ids = await self.game_repo.list_unanalyzed_game_ids(
                kwargs.get("source"),
                kwargs.get("username"),
            )

        if not game_ids:
            empty = {"analyzed": 0, "skipped": 0}
            await self.job_service.complete_job(job_id, empty)
            return empty

        return await self._run(job_id, game_ids, steps, concurrency)

    async def _run(
        self,
        job_id: str,
        game_ids: list[str],
        steps: list[str] | None,
        concurrency: int,
    ) -> dict[str, Any]:
        owns_coordinator = self._coordinator is None
        coordinator = self._coordinator or WorkCoordinator(
            self.analyzer.engine_path,
            concurrency,
        )
        if owns_coordinator:
            await coordinator.start()

        cancelled = asyncio.Event()
        watcher = asyncio.create_task(self._watch_cancellation(job_id, cancelled))

        try:  # noqa: WPS501 — owned-resource cleanup pattern: watcher + coordinator shutdown is unconditional.
            return await self.job_service.run_with_lifecycle(
                job_id,
                len(game_ids),
                lambda progress: self._submit_all(
                    game_ids,
                    steps,
                    coordinator,
                    cancelled,
                    progress,
                ),
            )
        finally:
            await self._shutdown(cancelled, watcher, coordinator, owns_coordinator)

    async def _submit_all(
        self,
        game_ids: list[str],
        steps: list[str] | None,
        coordinator: WorkCoordinator,
        cancelled: asyncio.Event,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        logger.info(
            "Starting parallel analysis of %d games",
            len(game_ids),
        )
        ctx = _AnalyzeContext(steps, len(game_ids), cancelled, progress)
        for game_id in game_ids:
            coordinator.submit(partial(self._process_one_game, game_id, ctx))
        await coordinator.drain()
        return ctx.results

    async def _process_one_game(
        self,
        game_id: str,
        ctx: _AnalyzeContext,
        engine: chess.engine.UciProtocol,
    ) -> None:
        if ctx.cancelled.is_set():
            return
        if await self.analysis_repo.analysis_exists(game_id):
            ctx.results["skipped"] += 1
            await self._tick_progress(ctx)
            return
        await self._analyze_one(game_id, ctx, engine)
        await self._tick_progress(ctx)

    async def _analyze_one(
        self,
        game_id: str,
        ctx: _AnalyzeContext,
        engine: chess.engine.UciProtocol,
    ) -> None:
        try:
            await self.analyzer.analyze_game(game_id, steps=ctx.steps, engine=engine)
            await self.game_repo.mark_game_analyzed(game_id)
        except Exception as exc:
            logger.error("Failed to analyze game %s: %s", game_id, exc)
            ctx.results["failed"] += 1
        else:
            ctx.results["analyzed"] += 1

    async def _tick_progress(self, ctx: _AnalyzeContext) -> None:
        ctx.processed += 1
        await ctx.progress(ctx.processed)

    async def _watch_cancellation(
        self,
        job_id: str,
        cancelled: asyncio.Event,
    ) -> None:
        if self._event_bus is None:
            return
        queue = await self._event_bus.subscribe(EventType.JOB_STATUS_CHANGED)
        try:  # noqa: WPS501 — paired subscribe/unsubscribe lifecycle; event bus has no context-manager API.
            while not cancelled.is_set():
                if await _next_failed_event_for(queue, job_id):
                    cancelled.set()
                    return
        finally:
            await self._event_bus.unsubscribe(queue, EventType.JOB_STATUS_CHANGED)

    async def _shutdown(
        self,
        cancelled: asyncio.Event,
        watcher: asyncio.Task[None],
        coordinator: WorkCoordinator,
        owns_coordinator: bool,
    ) -> None:
        cancelled.set()
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher
        if owns_coordinator:
            await coordinator.shutdown()


async def _next_failed_event_for(queue: asyncio.Queue, job_id: str) -> bool:
    """Returns True iff the next event (within 1s) is the FAILED transition for this job."""
    try:
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
    except TimeoutError:
        return False
    data = event.data
    return data.get("job_id") == job_id and data.get("status") == JOB_STATUS_FAILED
