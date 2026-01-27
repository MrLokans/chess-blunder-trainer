"""Service layer for job management with event publishing."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobEvent, StatsEvent
from blunder_tutor.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing background jobs with event publishing.

    This service wraps JobRepository and handles event publishing
    to decouple the repository from the event bus.
    """

    def __init__(self, job_repository: JobRepository, event_bus: EventBus):
        self.job_repository = job_repository
        self.event_bus = event_bus
        self._main_loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the main event loop for cross-thread event publishing.

        This should be called during application startup to enable
        event publishing from executor threads.
        """
        self._main_loop = loop

    def _publish_event(self, coro: Coroutine[Any, Any, None]) -> None:
        """Publish an event, handling both async and sync contexts.

        If called from within a running event loop, creates a task.
        If called from a thread without an event loop (e.g., executor),
        uses run_coroutine_threadsafe to schedule on the main loop.
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            loop.create_task(coro)
        except RuntimeError:
            # No running event loop in this thread
            if self._main_loop is not None and self._main_loop.is_running():
                # Schedule on the main loop from this thread
                asyncio.run_coroutine_threadsafe(coro, self._main_loop)
            else:
                # No way to publish, log and skip
                logger.debug("Cannot publish event: no event loop available")

    def create_job(
        self,
        job_type: str,
        username: str | None = None,
        source: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        max_games: int | None = None,
    ) -> str:
        job_id = self.job_repository.create_job(
            job_type=job_type,
            username=username,
            source=source,
            start_date=start_date,
            end_date=end_date,
            max_games=max_games,
        )

        event = JobEvent.create_status_changed(job_id, job_type, "pending")
        self._publish_event(self.event_bus.publish(event))

        return job_id

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        self.job_repository.update_job_status(job_id, status, error_message)

        job = self.job_repository.get_job(job_id)
        if job:
            event = JobEvent.create_status_changed(
                job_id=job_id,
                job_type=job["job_type"],
                status=status,
                error_message=error_message,
            )
            self._publish_event(self.event_bus.publish(event))

            # Emit stats updated event when job completes
            if status == "completed":
                stats_event = StatsEvent.create_stats_updated()
                self._publish_event(self.event_bus.publish(stats_event))

    def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        self.job_repository.update_job_progress(job_id, current, total)

        job = self.job_repository.get_job(job_id)
        if job:
            event = JobEvent.create_progress_updated(
                job_id=job_id,
                job_type=job["job_type"],
                current=current,
                total=total,
            )
            self._publish_event(self.event_bus.publish(event))

    def complete_job(
        self,
        job_id: str,
        result: dict[str, object],
    ) -> None:
        self.job_repository.complete_job(job_id, result)

        job = self.job_repository.get_job(job_id)
        if job:
            event = JobEvent.create_status_changed(
                job_id=job_id, job_type=job["job_type"], status="completed"
            )
            self._publish_event(self.event_bus.publish(event))

            # Emit stats updated event
            stats_event = StatsEvent.create_stats_updated()
            self._publish_event(self.event_bus.publish(stats_event))

    def get_job(self, job_id: str) -> dict[str, object] | None:
        return self.job_repository.get_job(job_id)

    def list_jobs(
        self,
        job_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        return self.job_repository.list_jobs(job_type, status, limit)

    def get_active_jobs(self) -> list[dict[str, object]]:
        return self.job_repository.get_active_jobs()

    def delete_job(self, job_id: str) -> bool:
        return self.job_repository.delete_job(job_id)
