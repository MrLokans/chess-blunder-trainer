from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    JOB_TYPE_DELETE_ALL_DATA,
    JOB_TYPE_IMPORT,
    JOB_TYPE_IMPORT_PGN,
    JOB_TYPE_SYNC,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EloRatingEvent, JobEvent, StatsEvent
from blunder_tutor.repositories.job_repository import JobRepository

type ProgressCallback = Callable[[int], Awaitable[None]]
type JobBody[T] = Callable[[ProgressCallback], Awaitable[T]]

logger = logging.getLogger(__name__)

PROGRESS_FLUSH_INTERVAL = 2.0

# Fallback user_key when a job has no associated username — keeps the
# stats-updated event addressable in single-user mode.
_DEFAULT_USER_KEY = "default"

# Job types whose completion changes `game_index_cache` rows (and therefore
# the rating-history derivation). Gating ELO emission to these avoids
# spurious cache churn on analyze/backfill/stats-sync jobs that don't
# touch game rows.
_GAME_DATASET_JOB_TYPES: frozenset[str] = frozenset(
    (
        JOB_TYPE_IMPORT,
        JOB_TYPE_SYNC,
        JOB_TYPE_IMPORT_PGN,
        JOB_TYPE_DELETE_ALL_DATA,
    )
)

_JOB_TYPE_KEY = "job_type"


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
        self._progress: dict[str, _ProgressState] = {}

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

        event = JobEvent.create_status_changed(job_id, job_type, JOB_STATUS_PENDING)
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
                job_type=job[_JOB_TYPE_KEY],
                status=status,
                error_message=error_message,
            )
            await self.event_bus.publish(event)

            if status == JOB_STATUS_COMPLETED:
                await self._publish_completion_fanout(job)

    async def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        state = self._progress.get(job_id)
        if state is None:
            job = await self.job_repository.get_job(job_id)
            job_type = job[_JOB_TYPE_KEY] if job else "unknown"
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
                job_id=job_id, job_type=job[_JOB_TYPE_KEY], status=JOB_STATUS_COMPLETED
            )
            await self.event_bus.publish(event)
            await self._publish_completion_fanout(job)

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        return await self.job_repository.get_job(job_id)

    async def run_with_lifecycle[T: dict[str, object]](  # noqa: WPS217 — lifecycle manager coordinates 5 status transitions; the await count IS the contract.
        self,
        job_id: str,
        total: int,
        body: JobBody[T],
    ) -> T:
        """Run `body` with the standard job lifecycle.

        Sets status to `running`, initializes progress at 0/total, then
        invokes `body(progress)` where `progress(current)` updates the
        job's progress. On success, marks the job complete with the body's
        return value. On exception, marks the job failed with the
        exception message and re-raises.
        """
        await self.update_job_status(job_id, JOB_STATUS_RUNNING)
        await self.update_job_progress(job_id, 0, total)

        async def progress(current: int) -> None:  # noqa: WPS430 — closure binds `job_id`/`total` so the body-callback signature stays `(current,) -> None`.
            await self.update_job_progress(job_id, current, total)

        try:
            result = await body(progress)
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            await self.update_job_status(job_id, JOB_STATUS_FAILED, str(exc))
            raise
        await self.complete_job(job_id, result)
        return result

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

    async def _publish_completion_fanout(self, job: dict[str, object]) -> None:
        user_key = job.get("username", _DEFAULT_USER_KEY) or _DEFAULT_USER_KEY
        await self.event_bus.publish(StatsEvent.create_stats_updated(user_key=user_key))
        if job.get(_JOB_TYPE_KEY) in _GAME_DATASET_JOB_TYPES:
            await self.event_bus.publish(
                EloRatingEvent.create_elo_rating_updated(
                    user_key=user_key, trigger="game_sync_completed"
                )
            )
