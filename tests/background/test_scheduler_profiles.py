from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import timedelta
from pathlib import Path

import pytest

from blunder_tutor.background.scheduler import (
    _maybe_dispatch_stats_sync_for_user,
    _maybe_dispatch_sync_for_user,
)
from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_TYPE_IMPORT,
    JOB_TYPE_STATS_SYNC,
    JOB_TYPE_SYNC,
)
from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    set_context,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import (
    ProfileStatSnapshot,
    SqliteProfileRepository,
)
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.utils.time import utcnow


@pytest.fixture
async def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def settings_repo(db_path: Path) -> AsyncGenerator[SettingsRepository]:
    repo = SettingsRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def profile_repo(db_path: Path) -> AsyncGenerator[SqliteProfileRepository]:
    repo = SqliteProfileRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def job_repo(db_path: Path) -> AsyncGenerator[JobRepository]:
    repo = JobRepository(db_path)
    yield repo
    await repo.close()


async def _seed_completed_sync_job(
    job_repo: JobRepository,
    *,
    job_id: str,
    source: str,
    username: str,
    completed_at: str,
) -> None:
    """Insert a `background_jobs` row that the per-(user, profile) game-sync
    fan-out reads via `JobRepository.get_last_completed_sync_at`. Done via
    raw SQL because the repo's `create_job` generates its own job_id and
    won't let us back-date `completed_at`.
    """
    conn = await job_repo.get_connection()
    await conn.execute(
        """
        INSERT INTO background_jobs (
            job_id, job_type, status, username, source, created_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            JOB_TYPE_SYNC,
            JOB_STATUS_COMPLETED,
            username,
            source,
            completed_at,
            completed_at,
        ),
    )
    await conn.commit()


@pytest.fixture
async def context(db_path: Path, event_bus: EventBus) -> AsyncGenerator[None]:
    ctx = DependencyContext(
        db_path=db_path,
        event_bus=event_bus,
        engine_path="/usr/bin/stockfish",
        user_id="testuser",
    )
    set_context(ctx)
    yield
    clear_context()


async def _drain_dispatched_events(
    queue: asyncio.Queue, *, timeout_s: float = 0.1
) -> list[dict]:
    """Pop everything currently on the queue. Times out fast since the
    dispatch path publishes synchronously before returning.
    """
    events: list[dict] = []
    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.02)
        except TimeoutError:
            break
        events.append(event.data)
    return events


def _hours_ago_iso(hours: float) -> str:
    return (utcnow() - timedelta(hours=hours)).isoformat()


class TestSyncDuePredicateTimezoneTolerance:
    """`_is_sync_due` must compare correctly whether `last_sync_iso` is
    tz-aware (post-migration writes go through `now_iso()` →
    ``...+00:00``) or tz-naive (legacy rows in user DBs were written
    with ``datetime.utcnow().isoformat()`` and have no offset). The
    routing through ``parse_dt`` is what keeps the subtraction from
    raising TypeError and crashing the whole scheduler tick.
    """

    async def test_dispatch_does_not_crash_on_tz_aware_synced_at(
        self,
        profile_repo: SqliteProfileRepository,
        event_bus: EventBus,
        context: None,
    ):
        profile = await profile_repo.create("lichess", "alice")
        # `upsert_stats` writes `synced_at = now_iso()` when the
        # snapshot's `synced_at` field is None — exactly the production
        # path the scheduler reads back later.
        await profile_repo.upsert_stats(
            profile.id,
            [ProfileStatSnapshot(mode="bullet", rating=2400, games_count=100)],
        )
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        # Default interval = 1h, the row was just written → fresh, not due.
        # The point of the test is that this completes WITHOUT raising
        # TypeError; the dispatch decision itself is incidental.
        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        assert await _drain_dispatched_events(queue) == []


class TestStatsSyncDispatch:
    async def test_due_profile_dispatches(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        context: None,
    ):
        profile = await profile_repo.create("lichess", "alice", make_primary=True)
        # Stats stale by 2h, interval is 1h → due.
        await profile_repo.upsert_stats(
            profile.id,
            [
                ProfileStatSnapshot(
                    mode="bullet",
                    rating=2400,
                    games_count=100,
                    synced_at=_hours_ago_iso(2),
                )
            ],
        )
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        events = await _drain_dispatched_events(queue)
        assert len(events) == 1
        assert events[0]["job_type"] == JOB_TYPE_STATS_SYNC
        assert events[0]["user_id"] == "testuser"
        assert events[0]["kwargs"] == {"profile_id": profile.id}

    async def test_fresh_profile_does_not_dispatch(
        self,
        profile_repo: SqliteProfileRepository,
        event_bus: EventBus,
        context: None,
    ):
        profile = await profile_repo.create("lichess", "alice")
        # Stats fresh — synced 10 minutes ago, interval default 1h → NOT due.
        await profile_repo.upsert_stats(
            profile.id,
            [
                ProfileStatSnapshot(
                    mode="bullet",
                    rating=2400,
                    games_count=100,
                    synced_at=_hours_ago_iso(10 / 60),
                )
            ],
        )
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        assert await _drain_dispatched_events(queue) == []

    async def test_profile_with_no_stats_dispatches_first_sync(
        self,
        profile_repo: SqliteProfileRepository,
        event_bus: EventBus,
        context: None,
    ):
        profile = await profile_repo.create("lichess", "alice")
        # No upsert_stats call → first-sync path.
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        events = await _drain_dispatched_events(queue)
        assert len(events) == 1
        assert events[0]["kwargs"] == {"profile_id": profile.id}

    async def test_auto_sync_disabled_profile_skipped(
        self,
        profile_repo: SqliteProfileRepository,
        event_bus: EventBus,
        context: None,
    ):
        target = await profile_repo.create("lichess", "alice", make_primary=True)
        skipped = await profile_repo.create("chesscom", "bob")
        await profile_repo.update_preferences(skipped.id, auto_sync_enabled=False)
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        events = await _drain_dispatched_events(queue)
        assert len(events) == 1
        assert events[0]["kwargs"] == {"profile_id": target.id}

    async def test_custom_interval_setting_respected(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        context: None,
    ):
        profile = await profile_repo.create("lichess", "alice")
        await profile_repo.upsert_stats(
            profile.id,
            [
                ProfileStatSnapshot(
                    mode="bullet",
                    rating=2400,
                    games_count=100,
                    synced_at=_hours_ago_iso(3),
                )
            ],
        )
        # Interval 6h — 3h-old stats are NOT due.
        await settings_repo.write_setting("stats_sync_interval_hours", "6")
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        assert await _drain_dispatched_events(queue) == []

    async def test_two_profiles_both_due_dispatches_two_events(
        self,
        profile_repo: SqliteProfileRepository,
        event_bus: EventBus,
        context: None,
    ):
        p1 = await profile_repo.create("lichess", "alice", make_primary=True)
        p2 = await profile_repo.create("chesscom", "alice")
        # Both stale.
        for profile_id in (p1.id, p2.id):
            await profile_repo.upsert_stats(
                profile_id,
                [
                    ProfileStatSnapshot(
                        mode="bullet",
                        rating=2400,
                        games_count=10,
                        synced_at=_hours_ago_iso(5),
                    )
                ],
            )
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_stats_sync_for_user(
            event_bus=event_bus, user_id="testuser"
        )

        events = await _drain_dispatched_events(queue)
        dispatched_profile_ids = sorted(e["kwargs"]["profile_id"] for e in events)
        assert dispatched_profile_ids == sorted([p1.id, p2.id])


class TestGameSyncFanOut:
    async def test_two_due_profiles_dispatch_two_events(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        context: None,
    ):
        await settings_repo.write_setting("auto_sync_enabled", "true")
        await settings_repo.write_setting("sync_interval_hours", "24")
        p1 = await profile_repo.create("lichess", "alice", make_primary=True)
        p2 = await profile_repo.create("chesscom", "alice")
        # No prior `background_jobs` rows → both profiles are first-sync overdue.
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id="testuser")

        events = await _drain_dispatched_events(queue)
        assert {event["job_type"] for event in events} == {JOB_TYPE_SYNC}
        dispatched_profile_ids = sorted(
            event["kwargs"]["profile_id"] for event in events
        )
        assert dispatched_profile_ids == sorted([p1.id, p2.id])

    async def test_one_fresh_one_stale_dispatches_only_stale(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        job_repo: JobRepository,
        event_bus: EventBus,
        context: None,
    ):
        await settings_repo.write_setting("auto_sync_enabled", "true")
        await settings_repo.write_setting("sync_interval_hours", "24")
        stale = await profile_repo.create("lichess", "alice", make_primary=True)
        fresh = await profile_repo.create("chesscom", "alice")
        await _seed_completed_sync_job(
            job_repo,
            job_id="stale-job",
            source=stale.platform,
            username=stale.username,
            completed_at=_hours_ago_iso(48),
        )
        await _seed_completed_sync_job(
            job_repo,
            job_id="fresh-job",
            source=fresh.platform,
            username=fresh.username,
            completed_at=_hours_ago_iso(2),
        )
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id="testuser")

        events = await _drain_dispatched_events(queue)
        assert len(events) == 1
        assert events[0]["kwargs"]["profile_id"] == stale.id

    async def test_global_auto_sync_disabled_no_dispatch(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        context: None,
    ):
        # Global kill-switch: even with profiles whose per-profile flag is
        # on, dispatch is suppressed.
        await settings_repo.write_setting("auto_sync_enabled", "false")
        await profile_repo.create("lichess", "alice", make_primary=True)
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id="testuser")

        assert await _drain_dispatched_events(queue) == []

    async def test_per_profile_auto_sync_disabled_skipped(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        context: None,
    ):
        await settings_repo.write_setting("auto_sync_enabled", "true")
        await settings_repo.write_setting("sync_interval_hours", "24")
        target = await profile_repo.create("lichess", "alice", make_primary=True)
        skipped = await profile_repo.create("chesscom", "alice")
        await profile_repo.update_preferences(skipped.id, auto_sync_enabled=False)
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id="testuser")

        events = await _drain_dispatched_events(queue)
        assert len(events) == 1
        assert events[0]["kwargs"]["profile_id"] == target.id

    async def test_dispatched_event_includes_job_id_for_lifecycle_tracking(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        job_repo: JobRepository,
        event_bus: EventBus,
        context: None,
    ):
        await settings_repo.write_setting("auto_sync_enabled", "true")
        await settings_repo.write_setting("sync_interval_hours", "24")
        profile = await profile_repo.create("lichess", "alice", make_primary=True)
        queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        await _maybe_dispatch_sync_for_user(event_bus=event_bus, user_id="testuser")

        events = await _drain_dispatched_events(queue)
        assert len(events) == 1
        # Game-sync, unlike stats-sync, creates a `background_jobs` row
        # and threads its UUID through to the runner so `run_with_lifecycle`
        # can advance PENDING → RUNNING → COMPLETED.
        job_id = events[0]["job_id"]
        assert job_id and not job_id.startswith("stats_sync-")
        # Verify the row was actually persisted.
        row = await job_repo.get_job(job_id)
        assert row is not None
        assert row["job_type"] in (JOB_TYPE_SYNC, JOB_TYPE_IMPORT)
        assert row["source"] == profile.platform
        assert row["username"] == profile.username
