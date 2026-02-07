from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobEvent, StatsEvent
from blunder_tutor.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)

PROGRESS_FLUSH_INTERVAL = 2.0


@dataclass
class _ProgressState:
    current: int = 0
    total: int = 0
    job_type: str = ""
    last_flushed_at: float = 0.0
    last_flushed_value: int = -1


class JobService:
    def __init__(self, job_repository: JobRepository, event_bus: EventBus):
        self.job_repository = job_repository
        self.event_bus = event_bus
        self._main_loop: asyncio.AbstractEventLoop | None = None
        self._progress: dict[str, _ProgressState] = {}

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._main_loop = loop

    def _publish_event(self, coro: Coroutine[Any, Any, None]) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            if self._main_loop is not None and self._main_loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, self._main_loop)
            else:
                logger.debug("Cannot publish event: no event loop available")

    async def create_job(
        self,
        job_type: str,
        username: str | None = None,
        source: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        max_games: int | None = None,
    ) -> str:
        job_id = await self.job_repository.create_job(
            job_type=job_type,
            username=username,
            source=source,
            start_date=start_date,
            end_date=end_date,
            max_games=max_games,
        )

        event = JobEvent.create_status_changed(job_id, job_type, "pending")
        await self.event_bus.publish(event)

        return job_id

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        await self.job_repository.update_job_status(job_id, status, error_message)

        job = await self.job_repository.get_job(job_id)
        if job:
            event = JobEvent.create_status_changed(
                job_id=job_id,
                job_type=job["job_type"],
                status=status,
                error_message=error_message,
            )
            await self.event_bus.publish(event)

            if status == "completed":
                stats_event = StatsEvent.create_stats_updated()
                await self.event_bus.publish(stats_event)

    async def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        state = self._progress.get(job_id)
        if state is None:
            job = await self.job_repository.get_job(job_id)
            job_type = job["job_type"] if job else "unknown"
            state = _ProgressState(job_type=job_type)
            self._progress[job_id] = state

        state.current = current
        state.total = total

        event = JobEvent.create_progress_updated(
            job_id=job_id,
            job_type=state.job_type,
            current=current,
            total=total,
        )
        await self.event_bus.publish(event)

        now = time.monotonic()
        should_flush = (
            now - state.last_flushed_at >= PROGRESS_FLUSH_INTERVAL
            or current == total
            or current == 0
        )
        if should_flush:
            await self.job_repository.update_job_progress(job_id, current, total)
            state.last_flushed_at = now
            state.last_flushed_value = current

    async def flush_progress(self, job_id: str) -> None:
        state = self._progress.pop(job_id, None)
        if state is not None and state.last_flushed_value != state.current:
            await self.job_repository.update_job_progress(
                job_id, state.current, state.total
            )

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, object],
    ) -> None:
        await self.flush_progress(job_id)
        await self.job_repository.complete_job(job_id, result)

        job = await self.job_repository.get_job(job_id)
        if job:
            event = JobEvent.create_status_changed(
                job_id=job_id, job_type=job["job_type"], status="completed"
            )
            await self.event_bus.publish(event)

            stats_event = StatsEvent.create_stats_updated()
            await self.event_bus.publish(stats_event)

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        return await self.job_repository.get_job(job_id)

    async def list_jobs(
        self,
        job_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        return await self.job_repository.list_jobs(job_type, status, limit)

    async def get_active_jobs(self) -> list[dict[str, object]]:
        return await self.job_repository.get_active_jobs()

    async def delete_job(self, job_id: str) -> bool:
        return await self.job_repository.delete_job(job_id)
