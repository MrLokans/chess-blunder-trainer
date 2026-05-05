from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from blunder_tutor.background.jobs.import_games import ImportGamesJob
from blunder_tutor.background.jobs.sync_games import SyncGamesJob
from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_TYPE_SYNC,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService


def _read_game_rows(db: Path) -> list[tuple]:
    with closing(sqlite3.connect(str(db))) as conn:
        return conn.execute(
            "SELECT game_id, source, username, profile_id "
            "FROM game_index_cache ORDER BY game_id"
        ).fetchall()


def _make_game(game_id: str, *, source: str, username: str) -> dict[str, object]:
    return {
        "id": game_id,
        "source": source,
        "username": username,
        "white": username,
        "black": "opponent",
        "result": "1-0",
        "date": "2026-04-30",
        "end_time_utc": "2026-04-30T12:00:00",
        "time_control": "180+0",
        "pgn_content": '[Event "Test"]\n1. e4 *',
    }


@pytest.fixture
async def profile_repo(db_path: Path) -> AsyncGenerator[SqliteProfileRepository]:
    repository = SqliteProfileRepository(db_path)
    yield repository
    await repository.close()


@pytest.fixture
async def settings_repo(db_path: Path) -> AsyncGenerator[SettingsRepository]:
    repository = SettingsRepository(db_path)
    yield repository
    await repository.close()


@pytest.fixture
async def game_repo(db_path: Path) -> AsyncGenerator[GameRepository]:
    repository = GameRepository(db_path)
    yield repository
    await repository.close()


@pytest.fixture
async def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def job_service(db_path: Path, event_bus: EventBus) -> AsyncGenerator[JobService]:
    job_repo = JobRepository(db_path)
    yield JobService(job_repository=job_repo, event_bus=event_bus)
    await job_repo.close()


GameRow = dict[str, object]
FetchResult = tuple[list[GameRow], dict]


def _stub_fetcher(captured: dict[str, Any], games: list[GameRow]):
    """Record the call args + return the supplied games tuple shape."""

    async def _fetch(
        username: str,
        max_games: int,
        *,
        since: Any = None,
        progress_callback: Any = None,
    ) -> FetchResult:
        captured["username"] = username
        captured["max_games"] = max_games
        captured["since"] = since
        if progress_callback is not None:
            await progress_callback(len(games), len(games))
        return games, {}

    return _fetch


class TestImportPerProfile:
    async def test_uses_profile_username_and_tags_inserted_rows(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await profile_repo.create("lichess", "alice", make_primary=True)
        captured: dict[str, Any] = {}
        games = [_make_game("g1", source="lichess", username="alice")]
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.import_games.lichess.fetch",
            _stub_fetcher(captured, games),
        )

        job = ImportGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        result = await job.execute(job_id="job-1", profile_id=profile.id)

        assert result["stored"] == 1
        assert captured["username"] == "alice"
        rows = _read_game_rows(db_path)
        assert rows == [("g1", "lichess", "alice", profile.id)]

    async def test_per_profile_max_games_overrides_global(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await profile_repo.create("lichess", "alice")
        await profile_repo.update_preferences(profile.id, sync_max_games=50)
        await settings_repo.write_setting("sync_max_games", "200")
        captured: dict[str, Any] = {}
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.import_games.lichess.fetch",
            _stub_fetcher(captured, []),
        )

        job = ImportGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        await job.execute(job_id="job-1", profile_id=profile.id)

        assert captured["max_games"] == 50

    async def test_null_profile_max_games_falls_back_to_global(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await profile_repo.create("lichess", "alice")
        # `sync_max_games` left NULL on the profile.
        await settings_repo.write_setting("sync_max_games", "200")
        captured: dict[str, Any] = {}
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.import_games.lichess.fetch",
            _stub_fetcher(captured, []),
        )

        job = ImportGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        await job.execute(job_id="job-1", profile_id=profile.id)

        assert captured["max_games"] == 200

    async def test_legacy_payload_without_profile_id_still_works(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        captured: dict[str, Any] = {}
        games = [_make_game("g-legacy", source="lichess", username="bob")]
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.import_games.lichess.fetch",
            _stub_fetcher(captured, games),
        )

        job = ImportGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        result = await job.execute(
            job_id="job-1", source="lichess", username="bob", max_games=50
        )

        assert result["stored"] == 1
        assert captured["username"] == "bob"
        # Legacy path leaves `profile_id` NULL on inserted rows.
        rows = _read_game_rows(db_path)
        assert rows == [("g-legacy", "lichess", "bob", None)]


class TestSyncPerProfile:
    async def test_with_profile_id_targets_only_that_profile(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        target = await profile_repo.create("lichess", "alice", make_primary=True)
        await profile_repo.create("chesscom", "alice")
        captured: dict[str, Any] = {}
        games = [_make_game("g-sync", source="lichess", username="alice")]
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.sync_games.lichess.fetch",
            _stub_fetcher(captured, games),
        )

        async def _chesscom_should_not_be_called(*_args, **_kwargs):
            raise AssertionError("chesscom fetcher invoked for lichess profile")

        monkeypatch.setattr(
            "blunder_tutor.background.jobs.sync_games.chesscom.fetch",
            _chesscom_should_not_be_called,
        )

        job_id = await job_service.create_job(
            job_type=JOB_TYPE_SYNC,
            username=target.username,
            source=target.platform,
        )
        job = SyncGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        result = await job.execute(job_id=job_id, profile_id=target.id)

        assert result["stored"] == 1
        rows = _read_game_rows(db_path)
        assert rows == [("g-sync", "lichess", "alice", target.id)]

    async def test_parent_job_lifecycled_to_completed(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Regression for the orphan-PENDING parent: prior to TREK-XX the
        # per-profile sync created a *child* job and lifecycled that, leaving
        # the caller-visible parent stuck at "pending" forever.
        profile = await profile_repo.create("lichess", "alice")
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.sync_games.lichess.fetch",
            _stub_fetcher({}, []),
        )

        parent_job_id = await job_service.create_job(
            job_type=JOB_TYPE_SYNC,
            username=profile.username,
            source=profile.platform,
        )
        job = SyncGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        await job.execute(job_id=parent_job_id, profile_id=profile.id)

        parent = await job_service.get_job(parent_job_id)
        assert parent is not None
        assert parent["status"] == JOB_STATUS_COMPLETED

        # No phantom child row should be created — the parent IS the sync job.
        sync_jobs = await job_service.list_jobs(job_type=JOB_TYPE_SYNC)
        assert [row["job_id"] for row in sync_jobs] == [parent_job_id]

    async def test_dispatch_without_profile_id_marks_parent_failed_and_raises(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
    ):
        # The legacy fan-out path (`/api/sync/start`) was removed; any sync
        # event reaching the runner without `profile_id` is a misconfigured
        # caller. The parent must be flipped to FAILED before raising so
        # the orphan-PENDING regression cannot recur.
        parent_job_id = await job_service.create_job(job_type=JOB_TYPE_SYNC)
        job = SyncGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )

        with pytest.raises(ValueError, match="profile_id"):
            await job.execute(job_id=parent_job_id)

        parent = await job_service.get_job(parent_job_id)
        assert parent is not None
        assert parent["status"] == JOB_STATUS_FAILED
        assert parent["error_message"] == "sync requires profile_id"

    async def test_missing_profile_completes_parent_with_zero_result(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
    ):
        # Delete-race / stale dispatch: a profile may be removed between
        # event publish and runner pickup. The parent must still complete
        # so the UI's job list doesn't accumulate orphan PENDING rows.
        parent_job_id = await job_service.create_job(job_type=JOB_TYPE_SYNC)
        job = SyncGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        result = await job.execute(job_id=parent_job_id, profile_id=999)

        assert result == {"stored": 0, "skipped": 0}
        parent = await job_service.get_job(parent_job_id)
        assert parent is not None
        assert parent["status"] == JOB_STATUS_COMPLETED

    async def test_per_profile_max_games_override(
        self,
        profile_repo: SqliteProfileRepository,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        job_service: JobService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        profile = await profile_repo.create("lichess", "alice")
        await profile_repo.update_preferences(profile.id, sync_max_games=25)
        await settings_repo.write_setting("sync_max_games", "100")
        captured: dict[str, Any] = {}
        monkeypatch.setattr(
            "blunder_tutor.background.jobs.sync_games.lichess.fetch",
            _stub_fetcher(captured, []),
        )

        job_id = await job_service.create_job(
            job_type=JOB_TYPE_SYNC,
            username=profile.username,
            source=profile.platform,
        )
        job = SyncGamesJob(
            job_service=job_service,
            settings_repo=settings_repo,
            game_repo=game_repo,
            profile_repo=profile_repo,
            user_id="testuser",
        )
        await job.execute(job_id=job_id, profile_id=profile.id)

        assert captured["max_games"] == 25
