from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any

from blunder_tutor.auth import UserId
from blunder_tutor.background.runners import JOB_RUNNERS
from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    set_context,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType, JobExecutionRequestEvent
from blunder_tutor.observability import count, distribution, start_span

if TYPE_CHECKING:
    from blunder_tutor.analysis.engine_pool import WorkCoordinator

logger = logging.getLogger(__name__)


DbPathResolver = Callable[[UserId], Path]


def _emit_job_completion(job_kind: str, status: str, elapsed_ms: float) -> None:
    """Chokepoint metrics are tagged only with `{kind, status}`; `user_id`/`job_id` go on
    the span to keep cardinality bounded. See docs/conventions/observability.md."""
    count("job.completed", tags={"kind": job_kind, "status": status})
    distribution("job.duration_ms", elapsed_ms, tags={"kind": job_kind})


class JobExecutor:
    """The engine pool is shared across users; each job is routed to its user's DB via
    `db_path_resolver`."""

    def __init__(
        self,
        event_bus: EventBus,
        db_path_resolver: DbPathResolver,
        engine_path: str,
        work_coordinator: WorkCoordinator | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._db_path_resolver = db_path_resolver
        self._engine_path = engine_path
        self._work_coordinator = work_coordinator
        self._shutdown = False
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._queue: asyncio.Queue | None = None

    async def subscribe(self) -> None:
        """Must be awaited before anyone publishes a job request, or events published
        during startup are dropped."""
        if self._queue is None:
            self._queue = await self._event_bus.subscribe(
                EventType.JOB_EXECUTION_REQUESTED
            )

    async def run(self) -> None:
        await self.subscribe()
        logger.info("JobExecutor started, listening for job execution requests")

        while not self._shutdown:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._handle_execution_request(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error processing job execution event: {e}")

    async def shutdown(self) -> None:
        logger.info("Shutting down JobExecutor...")
        self._shutdown = True

        if self._queue:
            await self._event_bus.unsubscribe(
                self._queue, EventType.JOB_EXECUTION_REQUESTED
            )

        if self._running_tasks:
            logger.info(f"Cancelling {len(self._running_tasks)} running tasks...")
            for task in self._running_tasks.values():
                task.cancel()
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)

        logger.info("JobExecutor shutdown complete")

    async def _handle_execution_request(self, event: JobExecutionRequestEvent) -> None:
        job_id = event.data["job_id"]
        job_type = event.data["job_type"]
        user_id: UserId = event.data["user_id"]
        kwargs = event.data.get("kwargs", {})

        logger.info(
            f"Received execution request for job {job_id} ({job_type}) user={user_id}"
        )

        task = asyncio.create_task(
            self._execute_job(job_id, job_type, user_id, kwargs),
            name=f"job-{job_id}",
        )
        self._running_tasks[job_id] = task
        task.add_done_callback(
            functools.partial(self._on_task_done, job_id=job_id, job_type=job_type)
        )

    def _on_task_done(self, task: asyncio.Task, *, job_id: str, job_type: str) -> None:
        # Retrieve .exception() to silence "never retrieved". The logger.error below
        # intentionally duplicates Sentry's capture so operators see it without Sentry;
        # don't dedupe.
        self._running_tasks.pop(job_id, None)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error(
                f"Job {job_id} ({job_type}) failed",
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    async def _execute_job(
        self,
        job_id: str,
        job_type: str,
        user_id: UserId,
        kwargs: dict[str, Any],
    ) -> None:
        runner = JOB_RUNNERS.get(job_type)
        if runner is None:
            logger.error(f"Unknown job type: {job_type}")
            return

        try:
            db_path = self._db_path_resolver(user_id)
        except Exception:
            logger.exception(
                f"Cannot resolve db_path for user {user_id} (job {job_id})"
            )
            return

        # Delete-race guard: connecting would re-create the user's dir (auto-mkdir in
        # `analysis.db._connect_async`) for events arriving between user deletion and
        # consumption.
        if not db_path.parent.exists():
            logger.info(
                f"Skipping job {job_id} ({job_type}): user {user_id} no longer exists"
            )
            return

        # Per-task contextvar: concurrent jobs don't see each other's db_path.
        context = DependencyContext(
            db_path=db_path,
            event_bus=self._event_bus,
            engine_path=self._engine_path,
            user_id=user_id,
            work_coordinator=self._work_coordinator,
        )
        set_context(context)

        # Top-level `start_span` becomes a transaction under sentry-sdk 2.x; revisit
        # through the facade if 3.x changes that.
        with start_span(job_type, op="job") as span:
            span.set_tag("user_id", str(user_id))
            span.set_data("job_id", job_id)
            count("job.started", tags={"kind": job_type})
            t0 = monotonic()
            status = "ok"
            try:
                logger.info(f"Starting execution of job {job_id} ({job_type})")
                # Exceptions propagate so AsyncioIntegration captures them under this
                # span.
                result = await runner(job_id=job_id, **kwargs)
                logger.info(f"Job {job_id} completed with result: {result}")
            except BaseException:
                # BaseException so `CancelledError` also flips status to error;
                # otherwise the metric miscounts.
                status = "error"
                raise
            finally:
                clear_context()
                _emit_job_completion(job_type, status, (monotonic() - t0) * 1000.0)
