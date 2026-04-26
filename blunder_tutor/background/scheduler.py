from __future__ import annotations

import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Annotated

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fast_depends import Depends, inject

from blunder_tutor.auth import UserId
from blunder_tutor.background.executor import DbPathResolver
from blunder_tutor.constants import JOB_TYPE_SYNC
from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    get_job_service,
    get_settings_repository,
    set_context,
)
from blunder_tutor.events import EventBus, JobExecutionRequestEvent
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)

DEFAULT_TICK_SECONDS = 300  # 5 min — see status doc + TREK-38 D2.

UserLister = Callable[[], Awaitable[list[UserId]]]


@inject
async def _maybe_dispatch_sync_for_user(
    event_bus: EventBus,
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    job_service: Annotated[JobService, Depends(get_job_service)],
    user_id: UserId,
) -> None:
    """Read this user's settings and publish a sync-execution event if
    auto-sync is enabled and the configured interval has elapsed since
    ``last_sync_timestamp``. Caller must have already set the
    :class:`DependencyContext` for ``user_id`` before invoking — this
    function is per-user-scoped via the ambient context."""
    settings = await settings_repo.get_all_settings()
    if not _is_feature_enabled(settings, "auto.sync"):
        return
    if settings.get("auto_sync_enabled") != "true":
        return
    interval_hours_str = settings.get("sync_interval_hours")
    interval_hours = int(interval_hours_str) if interval_hours_str else 24

    if not _is_sync_due(settings.get("last_sync_timestamp"), interval_hours):
        return

    job_id = await job_service.create_job(job_type=JOB_TYPE_SYNC, username=user_id)
    event = JobExecutionRequestEvent.create(
        job_id=job_id, job_type=JOB_TYPE_SYNC, user_id=user_id
    )
    await event_bus.publish(event)
    logger.info(f"Auto-sync dispatched for user {user_id} (job {job_id})")


def _is_feature_enabled(settings: dict[str, str | None], feature_key: str) -> bool:
    return settings.get(f"feature_{feature_key}") != "false"


def _is_sync_due(last_sync_iso: str | None, interval_hours: int) -> bool:
    """No prior sync ⇒ catch up on next tick. With a prior sync, fire
    once the interval has elapsed.
    """
    if not last_sync_iso:
        return True
    try:
        last = datetime.fromisoformat(last_sync_iso)
    except ValueError:
        # Corrupt timestamp — treat as overdue rather than blocking forever.
        return True
    return datetime.utcnow() - last >= timedelta(hours=interval_hours)


async def _fanout_tick(
    event_bus: EventBus,
    engine_path: str,
    list_users: UserLister,
    db_path_resolver: DbPathResolver,
) -> None:
    """One scheduler tick. Walks users sequentially and dispatches sync
    jobs for any user whose settings say a sync is due.

    Sequential — not ``asyncio.gather`` — to bound concurrent SQLite
    connections to the auth DB and the per-user DBs. The work per user
    is a single settings read plus an event publish, so the sequential
    pass is microseconds-fast even at thousands of users; cross-user
    failure isolation comes from the inner try/except, not from
    parallelism.
    """
    try:
        user_ids = await list_users()
    except Exception:
        logger.exception("Auto-sync tick: failed to enumerate users")
        return

    for user_id in user_ids:
        try:
            db_path = db_path_resolver(user_id)
        except Exception:
            logger.exception(f"Auto-sync tick: db_path resolve failed for {user_id}")
            continue

        # Delete-race guard. ``list_users`` is read once at tick start;
        # a user can be deleted before this loop iteration reaches them.
        # Opening their DB would silently re-create the data directory
        # (see executor.py for the same guard).
        if not db_path.parent.exists():
            logger.info(f"Auto-sync tick: skipping deleted user {user_id}")
            continue

        context = DependencyContext(
            db_path=db_path,
            event_bus=event_bus,
            engine_path=engine_path,
            user_id=user_id,
        )
        set_context(context)
        try:
            await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id=user_id)
        except Exception:
            logger.exception(f"Auto-sync tick: dispatch failed for user {user_id}")
        finally:
            clear_context()


class BackgroundScheduler:
    """Multi-user fanout scheduler. One APScheduler job ticks every
    ``tick_seconds``; each tick walks the user list and dispatches
    sync jobs for users whose per-user settings say a sync is due.

    Stateless w.r.t. user lifecycle: signups and account deletions
    take effect on the next tick with no add/remove plumbing.
    """

    def __init__(
        self,
        event_bus: EventBus,
        engine_path: str,
        list_users: UserLister,
        db_path_resolver: DbPathResolver,
        tick_seconds: int = DEFAULT_TICK_SECONDS,
    ) -> None:
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {"coalesce": True, "max_instances": 1}

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores, executors=executors, job_defaults=job_defaults
        )
        self._event_bus = event_bus
        self._engine_path = engine_path
        self._list_users = list_users
        self._db_path_resolver = db_path_resolver
        self._tick_seconds = tick_seconds

    def start(self) -> None:
        with contextlib.suppress(Exception):
            self.scheduler.remove_job("auto_sync_fanout")

        self.scheduler.add_job(
            func=_fanout_tick,
            trigger=IntervalTrigger(seconds=self._tick_seconds),
            id="auto_sync_fanout",
            replace_existing=True,
            kwargs={
                "event_bus": self._event_bus,
                "engine_path": self._engine_path,
                "list_users": self._list_users,
                "db_path_resolver": self._db_path_resolver,
            },
        )

        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
