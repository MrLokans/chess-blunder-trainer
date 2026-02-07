from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from blunder_tutor.background.runners import JOB_RUNNERS
from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    set_context,
)
from blunder_tutor.events import EventBus, EventType, JobExecutionRequestEvent

if TYPE_CHECKING:
    from blunder_tutor.analysis.engine_pool import WorkCoordinator

logger = logging.getLogger(__name__)


class JobExecutor:
    """Executes background jobs using FastDepends for dependency injection.

    Subscribes to JOB_EXECUTION_REQUESTED events and uses injectable
    job runners that automatically resolve and cleanup dependencies.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_path: Path,
        engine_path: str,
        work_coordinator: WorkCoordinator | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._db_path = db_path
        self._engine_path = engine_path
        self._work_coordinator = work_coordinator
        self._shutdown = False
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._queue: asyncio.Queue | None = None

    async def start(self) -> None:
        self._queue = await self._event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)
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

    async def _handle_execution_request(self, event: JobExecutionRequestEvent) -> None:
        job_id = event.data["job_id"]
        job_type = event.data["job_type"]
        kwargs = event.data.get("kwargs", {})

        logger.info(f"Received execution request for job {job_id} ({job_type})")

        task = asyncio.create_task(
            self._execute_job(job_id, job_type, kwargs),
            name=f"job-{job_id}",
        )
        self._running_tasks[job_id] = task
        task.add_done_callback(lambda t: self._running_tasks.pop(job_id, None))

    async def _execute_job(
        self, job_id: str, job_type: str, kwargs: dict[str, Any]
    ) -> None:
        runner = JOB_RUNNERS.get(job_type)
        if runner is None:
            logger.error(f"Unknown job type: {job_type}")
            return

        # Set up the dependency context for this job
        context = DependencyContext(
            db_path=self._db_path,
            event_bus=self._event_bus,
            engine_path=self._engine_path,
            work_coordinator=self._work_coordinator,
        )
        set_context(context)

        try:
            logger.info(f"Starting execution of job {job_id} ({job_type})")
            # FastDepends @inject handles all dependency resolution and cleanup
            result = await runner(job_id=job_id, **kwargs)
            logger.info(f"Job {job_id} completed with result: {result}")

        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")

        finally:
            clear_context()

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
