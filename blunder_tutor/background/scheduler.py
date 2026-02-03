from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Annotated

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fast_depends import Depends, inject

from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    get_job_service,
    set_context,
)
from blunder_tutor.events import EventBus, JobExecutionRequestEvent
from blunder_tutor.services.job_service import JobService


@inject
async def _create_sync_job(
    event_bus: EventBus,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> None:
    job_id = await job_service.create_job(job_type="sync")
    event = JobExecutionRequestEvent.create(job_id=job_id, job_type="sync")
    await event_bus.publish(event)


async def _run_scheduled_sync(
    db_path: Path, event_bus: EventBus, engine_path: str
) -> None:
    context = DependencyContext(
        db_path=db_path,
        event_bus=event_bus,
        engine_path=engine_path,
    )
    set_context(context)
    try:
        await _create_sync_job(event_bus=event_bus)
    finally:
        clear_context()


class BackgroundScheduler:
    def __init__(self, db_path: Path, event_bus: EventBus, engine_path: str):
        # Use in-memory job store to avoid serialization issues
        # Jobs are re-created on startup from settings anyway
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {"coalesce": True, "max_instances": 1}

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores, executors=executors, job_defaults=job_defaults
        )
        self._db_path = db_path
        self._event_bus = event_bus
        self._engine_path = engine_path

    def start(self, settings: dict[str, str | None]) -> None:
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync")

        if settings.get("auto_sync_enabled") == "true":
            interval_hours_str = settings.get("sync_interval_hours")
            interval_hours = int(interval_hours_str) if interval_hours_str else 24

            self.scheduler.add_job(
                func=_run_scheduled_sync,
                trigger=IntervalTrigger(hours=interval_hours),
                id="auto_sync",
                replace_existing=True,
                args=[self._db_path, self._event_bus, self._engine_path],
            )

        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

    def update_jobs(self, settings: dict[str, str | None]) -> None:
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync")

        if settings.get("auto_sync_enabled") == "true":
            interval_hours_str = settings.get("sync_interval_hours")
            interval_hours = int(interval_hours_str) if interval_hours_str else 24

            self.scheduler.add_job(
                func=_run_scheduled_sync,
                trigger=IntervalTrigger(hours=interval_hours),
                id="auto_sync",
                replace_existing=True,
                args=[self._db_path, self._event_bus, self._engine_path],
            )
