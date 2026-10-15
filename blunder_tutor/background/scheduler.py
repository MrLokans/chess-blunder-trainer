from __future__ import annotations

import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Annotated

import sentry_sdk
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fast_depends import Depends, inject

from blunder_tutor.auth import UserId
from blunder_tutor.background.executor import DbPathResolver
from blunder_tutor.constants import JOB_TYPE_STATS_SYNC, JOB_TYPE_SYNC
from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    get_job_repository,
    get_job_service,
    get_profile_repository,
    get_settings_repository,
    set_context,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobExecutionRequestEvent
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService
from blunder_tutor.utils.time import parse_dt, utcnow

logger = logging.getLogger(__name__)

DEFAULT_TICK_SECONDS = 300  # 5 min — see status doc + TREK-38 D2.
DEFAULT_STATS_SYNC_INTERVAL_HOURS = 1  # Mirrors migration 009 default.

UserLister = Callable[[], Awaitable[list[UserId]]]


@inject
async def _maybe_dispatch_sync_for_user(  # noqa: WPS211 — FastDepends @inject; each repo is a parameter the framework resolves.
    event_bus: EventBus,
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    job_service: Annotated[JobService, Depends(get_job_service)],
    profile_repo: Annotated[SqliteProfileRepository, Depends(get_profile_repository)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
    user_id: UserId,
) -> None:
    """The global `auto_sync_enabled` is the kill-switch. Per-profile lookups are N+1 on
    purpose to keep repository boundaries clean; fold them into
    `list_auto_sync_candidates` with a JOIN if profiles per user pass ~10."""
    settings = await settings_repo.get_all_settings()
    if not _is_feature_enabled(settings, "auto.sync"):
        return
    if settings.get("auto_sync_enabled") != "true":
        return
    interval_hours_str = settings.get("sync_interval_hours")
    interval_hours = int(interval_hours_str) if interval_hours_str else 24

    candidates = await profile_repo.list_auto_sync_candidates()
    for candidate in candidates:
        last_sync_at = await job_repo.get_last_completed_sync_at(
            candidate.platform, candidate.username
        )
        if not _is_sync_due(last_sync_at, interval_hours):
            continue
        job_id = await job_service.create_job(
            job_type=JOB_TYPE_SYNC,
            username=candidate.username,
            source=candidate.platform,
        )
        event = JobExecutionRequestEvent.create(
            job_id=job_id,
            job_type=JOB_TYPE_SYNC,
            user_id=user_id,
            profile_id=candidate.profile_id,
        )
        await event_bus.publish(event)
        logger.info(
            f"Auto-sync dispatched for user {user_id} "
            f"profile={candidate.profile_id} job={job_id}"
        )


def _is_feature_enabled(settings: dict[str, str | None], feature_key: str) -> bool:
    return settings.get(f"feature_{feature_key}") != "false"


@inject
async def _maybe_dispatch_stats_sync_for_user(
    event_bus: EventBus,
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    profile_repo: Annotated[SqliteProfileRepository, Depends(get_profile_repository)],
    user_id: UserId,
) -> None:
    """Fire-and-forget: no `background_jobs` row."""
    settings = await settings_repo.get_all_settings()
    interval_str = settings.get("stats_sync_interval_hours")
    interval_hours = (
        int(interval_str) if interval_str else DEFAULT_STATS_SYNC_INTERVAL_HOURS
    )

    candidates = await profile_repo.list_auto_sync_candidates()
    for candidate in candidates:
        if not _is_sync_due(candidate.last_stats_sync_at, interval_hours):
            continue
        synthetic_job_id = f"stats_sync-{user_id}-{candidate.profile_id}"
        event = JobExecutionRequestEvent.create(
            job_id=synthetic_job_id,
            job_type=JOB_TYPE_STATS_SYNC,
            user_id=user_id,
            profile_id=candidate.profile_id,
        )
        await event_bus.publish(event)
        logger.info(
            f"stats_sync dispatched for user {user_id} "
            f"profile={candidate.profile_id} job={synthetic_job_id}"
        )


def _is_sync_due(last_sync_iso: str | None, interval_hours: int) -> bool:
    if not last_sync_iso:
        return True
    try:
        last = parse_dt(last_sync_iso)
    except ValueError:
        # Corrupt timestamp — treat as overdue rather than blocking forever.
        return True
    return utcnow() - last >= timedelta(hours=interval_hours)


async def _dispatch_one_user(
    event_bus: EventBus,
    engine_path: str,
    user_id: UserId,
    db_path_resolver: DbPathResolver,
) -> None:
    try:
        db_path = db_path_resolver(user_id)
    except Exception:
        logger.exception(f"Auto-sync tick: db_path resolve failed for {user_id}")
        return

    # Delete-race guard: the user may be deleted since `list_users`; opening their DB
    # would re-create the data dir (see executor.py).
    if not db_path.parent.exists():
        logger.info(f"Auto-sync tick: skipping deleted user {user_id}")
        return

    context = DependencyContext(
        db_path=db_path,
        event_bus=event_bus,
        engine_path=engine_path,
        user_id=user_id,
    )
    set_context(context)
    try:
        await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id=user_id)
        await _maybe_dispatch_stats_sync_for_user(event_bus=event_bus, user_id=user_id)
    except Exception:
        logger.exception(f"Auto-sync tick: dispatch failed for user {user_id}")
    finally:
        clear_context()


@sentry_sdk.monitor(monitor_slug="bt-scheduler-tick")
async def _fanout_tick(
    event_bus: EventBus,
    engine_path: str,
    list_users: UserLister,
    db_path_resolver: DbPathResolver,
) -> None:
    """Sequential to bound concurrent SQLite connections; the inner try/except isolates
    failures. `@sentry_sdk.monitor` alerts when the check-in goes missing (config lives
    in the Sentry UI)."""
    try:
        user_ids = await list_users()
    except Exception:
        logger.exception("Auto-sync tick: failed to enumerate users")
        return

    for user_id in user_ids:
        await _dispatch_one_user(
            event_bus=event_bus,
            engine_path=engine_path,
            user_id=user_id,
            db_path_resolver=db_path_resolver,
        )


class BackgroundScheduler:
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
