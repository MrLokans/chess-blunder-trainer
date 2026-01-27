from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from blunder_tutor.background.jobs.sync_games import SyncGamesJob


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
        self._sync_job: SyncGamesJob | None = None

    def configure_sync_job(self, sync_job: SyncGamesJob) -> None:
        """Configure the sync job instance for scheduled execution.

        Args:
            sync_job: The sync job instance to use for scheduled syncs.
        """
        self._sync_job = sync_job

    async def _run_scheduled_sync(self) -> None:
        """Run the scheduled sync job."""
        if self._sync_job is not None:
            # job_id is created per-source inside execute
            await self._sync_job.execute(job_id="")

    def start(self, settings: dict[str, str | None]) -> None:
        """Start the scheduler with the given settings.

        Args:
            settings: Dictionary of settings including auto_sync_enabled
                      and sync_interval_hours.
        """
        # Remove existing auto-sync job if present
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync")

        # Configure automatic sync job
        if settings.get("auto_sync_enabled") == "true" and self._sync_job is not None:
            interval_hours_str = settings.get("sync_interval_hours")
            interval_hours = int(interval_hours_str) if interval_hours_str else 24

            self.scheduler.add_job(
                func=self._run_scheduled_sync,
                trigger=IntervalTrigger(hours=interval_hours),
                id="auto_sync",
                replace_existing=True,
            )

        # Only start if not already running
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

    def update_jobs(self, settings: dict[str, str | None]) -> None:
        """Update scheduled jobs based on new settings.

        Args:
            settings: Dictionary of settings including auto_sync_enabled
                      and sync_interval_hours.
        """
        # Remove existing auto-sync job
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync")

        # Add new job if enabled
        if settings.get("auto_sync_enabled") == "true" and self._sync_job is not None:
            interval_hours_str = settings.get("sync_interval_hours")
            interval_hours = int(interval_hours_str) if interval_hours_str else 24

            self.scheduler.add_job(
                func=self._run_scheduled_sync,
                trigger=IntervalTrigger(hours=interval_hours),
                id="auto_sync",
                replace_existing=True,
            )
