from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from blunder_tutor.background.jobs.stats_sync import StatsSyncJob
from blunder_tutor.fetchers import RateLimitError
from blunder_tutor.repositories.profile import (
    ProfileStatSnapshot,
    SqliteProfileRepository,
)


@pytest.fixture
async def repo(db_path: Path) -> AsyncGenerator[SqliteProfileRepository]:
    repository = SqliteProfileRepository(db_path)
    yield repository
    await repository.close()


def _read_stats_rows(db: Path, profile_id: int) -> list[tuple]:
    with closing(sqlite3.connect(str(db))) as conn:
        return conn.execute(
            "SELECT mode, rating, games_count FROM profile_stats "
            "WHERE profile_id = ? ORDER BY mode",
            (profile_id,),
        ).fetchall()


def _read_last_validated_at(db: Path, profile_id: int) -> str | None:
    with closing(sqlite3.connect(str(db))) as conn:
        row = conn.execute(
            "SELECT last_validated_at FROM profile WHERE id = ?", (profile_id,)
        ).fetchone()
    return None if row is None else row[0]


def _stub_fetch(snapshots: list[ProfileStatSnapshot]):
    async def _fetch(_username: str) -> list[ProfileStatSnapshot]:
        return snapshots

    return _fetch


def _stub_rate_limit(platform: str):
    async def _fetch(_username: str) -> list[ProfileStatSnapshot]:
        raise RateLimitError(platform)

    return _fetch


class TestStatsSyncJobLichess:
    async def test_happy_path_upserts_stats_and_touches_last_validated(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await repo.create("lichess", "alice", make_primary=True)
        snapshots = [
            ProfileStatSnapshot(mode="bullet", rating=2400, games_count=5000),
            ProfileStatSnapshot(mode="blitz", rating=2300, games_count=12000),
        ]
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
            _stub_fetch(snapshots),
        )

        job = StatsSyncJob(profile_repo=repo)
        result = await job.execute(job_id="job-1", profile_id=profile.id)

        assert result == {"deferred": False, "stored": 2}
        rows = _read_stats_rows(db_path, profile.id)
        assert rows == [("blitz", 2300, 12000), ("bullet", 2400, 5000)]
        assert _read_last_validated_at(db_path, profile.id) is not None

    async def test_upsert_overwrites_existing_snapshot(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await repo.create("lichess", "alice")
        await repo.upsert_stats(
            profile.id,
            [ProfileStatSnapshot(mode="bullet", rating=2000, games_count=100)],
        )
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
            _stub_fetch(
                [ProfileStatSnapshot(mode="bullet", rating=2500, games_count=200)],
            ),
        )

        job = StatsSyncJob(profile_repo=repo)
        await job.execute(job_id="job-1", profile_id=profile.id)

        rows = _read_stats_rows(db_path, profile.id)
        assert rows == [("bullet", 2500, 200)]


class TestStatsSyncJobChessCom:
    async def test_happy_path_routes_to_chesscom_fetcher(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await repo.create("chesscom", "alice")
        snapshots = [
            ProfileStatSnapshot(mode="rapid", rating=1900, games_count=300),
        ]

        # Lichess fetcher must NOT be called for a chesscom profile.
        async def _lichess_should_not_be_called(_username: str) -> Any:
            raise AssertionError("lichess fetcher invoked for chesscom profile")

        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
            _lichess_should_not_be_called,
        )
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.chesscom.fetch_user_stats",
            _stub_fetch(snapshots),
        )

        job = StatsSyncJob(profile_repo=repo)
        result = await job.execute(job_id="job-1", profile_id=profile.id)

        assert result == {"deferred": False, "stored": 1}
        assert _read_stats_rows(db_path, profile.id) == [("rapid", 1900, 300)]


class TestStatsSyncJobRateLimit:
    async def test_rate_limit_caught_no_rows_written_no_validation_touch(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await repo.create("lichess", "alice")
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
            _stub_rate_limit("lichess"),
        )

        job = StatsSyncJob(profile_repo=repo)
        result = await job.execute(job_id="job-1", profile_id=profile.id)

        assert result == {"deferred": True, "stored": 0}
        assert _read_stats_rows(db_path, profile.id) == []
        assert _read_last_validated_at(db_path, profile.id) is None


class TestStatsSyncJobMissingProfile:
    async def test_missing_profile_is_graceful_noop(
        self,
        repo: SqliteProfileRepository,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # No profile created — id 999 doesn't exist.
        async def _should_not_be_called(_username: str) -> Any:
            raise AssertionError("fetcher invoked for missing profile")

        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
            _should_not_be_called,
        )
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.stats_sync.chesscom.fetch_user_stats",
            _should_not_be_called,
        )

        job = StatsSyncJob(profile_repo=repo)
        result = await job.execute(job_id="job-1", profile_id=999)

        assert result == {"deferred": False, "stored": 0, "missing": True}
