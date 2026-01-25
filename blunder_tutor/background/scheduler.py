from __future__ import annotations

import contextlib
from pathlib import Path

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


class BackgroundScheduler:
    def __init__(self, data_dir: Path, db_path: Path):
        self.data_dir = data_dir
        db_url = f"sqlite:///{str(db_path)}"

        jobstores = {
            "default": SQLAlchemyJobStore(url=db_url, tablename="apscheduler_jobs")
        }
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {"coalesce": True, "max_instances": 1}

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores, executors=executors, job_defaults=job_defaults
        )

    def start(self, settings: dict[str, str | None], event_bus=None) -> None:
        from blunder_tutor.background.jobs import sync_games_job

        self.event_bus = event_bus

        # Remove existing auto-sync job if present
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync")

        # Configure automatic sync job
        if settings.get("auto_sync_enabled") == "true":
            interval_hours_str = settings.get("sync_interval_hours")
            interval_hours = int(interval_hours_str) if interval_hours_str else 24

            self.scheduler.add_job(
                func=sync_games_job,
                trigger=IntervalTrigger(hours=interval_hours),
                id="auto_sync",
                replace_existing=True,
                kwargs={"data_dir": self.data_dir, "event_bus": event_bus},
            )

        # Only start if not already running
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

    def update_jobs(self, settings: dict[str, str | None], event_bus=None) -> None:
        from blunder_tutor.background.jobs import sync_games_job

        # Update stored event_bus if provided
        if event_bus is not None:
            self.event_bus = event_bus

        # Remove existing auto-sync job
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync")

        # Add new job if enabled
        if settings.get("auto_sync_enabled") == "true":
            interval_hours_str = settings.get("sync_interval_hours")
            interval_hours = int(interval_hours_str) if interval_hours_str else 24

            self.scheduler.add_job(
                func=sync_games_job,
                trigger=IntervalTrigger(hours=interval_hours),
                id="auto_sync",
                replace_existing=True,
                kwargs={"data_dir": self.data_dir, "event_bus": self.event_bus},
            )
