from __future__ import annotations

import asyncio
import sqlite3
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from blunder_tutor.constants import JOB_TYPE_IMPORT
from blunder_tutor.events.event_types import EventType
from blunder_tutor.fetchers import ExistenceCheck, RateLimitError
from blunder_tutor.fetchers.resilience import RetryableHTTPError
from blunder_tutor.repositories.profile import (
    ProfileStatSnapshot,
    SqliteProfileRepository,
)


def _patch_existence_raising(
    monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    async def fake(_platform: str, _username: str) -> ExistenceCheck:
        raise exc

    monkeypatch.setattr(
        "blunder_tutor.web.api._profile_helpers.check_username_existence", fake
    )


def _patch_existence(monkeypatch: pytest.MonkeyPatch, result: ExistenceCheck) -> None:
    async def fake(_platform: str, _username: str) -> ExistenceCheck:
        return result

    # All three handlers route through `_profile_helpers` for the upstream
    # existence check — single patch site.
    monkeypatch.setattr(
        "blunder_tutor.web.api._profile_helpers.check_username_existence", fake
    )


def _insert_completed_job(db_path: Path, *, username: str, completed_at: str) -> None:
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.execute(
            "INSERT INTO background_jobs "
            "(job_id, job_type, status, username, source, "
            " created_at, completed_at) "
            "VALUES (?, 'import', 'completed', ?, 'lichess', ?, ?)",
            (f"job-{completed_at}", username, completed_at, completed_at),
        )
        conn.commit()


class TestListProfiles:
    def test_empty(self, app: TestClient) -> None:
        response = app.get("/api/profiles")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"profiles": []}

    async def test_single_profile_with_stats(
        self,
        app: TestClient,
        db_path: Path,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")
            await repo.upsert_stats(
                profile.id,
                [
                    ProfileStatSnapshot(mode="bullet", rating=2400, games_count=1200),
                    ProfileStatSnapshot(mode="blitz", rating=2300, games_count=850),
                ],
            )

        response = app.get("/api/profiles")
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert len(body["profiles"]) == 1

        item = body["profiles"][0]
        assert item["id"] == profile.id
        assert item["platform"] == "lichess"
        assert item["username"] == "alice"
        assert item["is_primary"] is True
        assert item["preferences"] == {
            "auto_sync_enabled": True,
            "sync_max_games": None,
        }
        modes = {s["mode"] for s in item["stats"]}
        assert modes == {"bullet", "blitz"}
        assert item["last_stats_sync_at"] is not None
        # No background_jobs rows yet → last_game_sync_at is None.
        assert item["last_game_sync_at"] is None

    async def test_last_game_sync_at_resolves_from_jobs(
        self,
        app: TestClient,
        db_path: Path,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            await repo.create("lichess", "alice")
        _insert_completed_job(
            db_path, username="alice", completed_at="2026-04-29T12:00:00"
        )
        _insert_completed_job(
            db_path, username="alice", completed_at="2026-04-30T08:00:00"
        )

        response = app.get("/api/profiles")
        item = response.json()["profiles"][0]
        assert item["last_game_sync_at"] == "2026-04-30T08:00:00"


class TestCreateProfile:
    def test_happy_path_returns_created_profile(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))

        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.CREATED

        body = response.json()
        assert body["platform"] == "lichess"
        assert body["username"] == "alice"
        assert body["is_primary"] is True  # First profile auto-primary.
        assert not body["stats"]
        assert body["last_game_sync_at"] is None
        assert body["last_stats_sync_at"] is None
        assert body["last_validated_at"] is not None

    def test_lowercases_username_in_response(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "AliceCarlsen"},
        )
        assert response.json()["username"] == "alicecarlsen"

    def test_make_primary_demotes_existing(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        first = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        ).json()
        second = app.post(
            "/api/profiles",
            json={
                "platform": "lichess",
                "username": "bob",
                "make_primary": True,
            },
        ).json()
        assert second["is_primary"] is True

        listing = app.get("/api/profiles").json()["profiles"]
        by_id = {p["id"]: p for p in listing}
        assert by_id[first["id"]]["is_primary"] is False
        assert by_id[second["id"]]["is_primary"] is True

    def test_duplicate_returns_409(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.CONFLICT
        body = response.json()
        assert "profile_id" in body["detail"]

    def test_nonexistent_username_returns_422(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=False, rate_limited=False))
        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "ghostuser"},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_rate_limited_returns_503(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=False, rate_limited=True))
        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        body = response.json()
        assert "rate" in body["detail"].lower()

    def test_invalid_platform_returns_422(self, app: TestClient) -> None:
        response = app.post(
            "/api/profiles",
            json={"platform": "fide", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_duplicate_check_skips_upstream(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )

        # Re-patch to a result that would fail (rate-limited) — duplicate
        # check should fire first and never reach the upstream.
        _patch_existence(monkeypatch, ExistenceCheck(exists=False, rate_limited=True))
        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.CONFLICT

    def test_upstream_5xx_returns_502(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        response_500 = MagicMock()
        response_500.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        _patch_existence_raising(monkeypatch, RetryableHTTPError(response_500))

        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY

    def test_upstream_403_returns_502(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        request = MagicMock()
        forbidden = MagicMock()
        forbidden.status_code = HTTPStatus.FORBIDDEN
        _patch_existence_raising(
            monkeypatch,
            httpx.HTTPStatusError("403", request=request, response=forbidden),
        )

        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY


class TestPatchProfile:
    async def _create(self, db_path: Path, platform: str, username: str) -> int:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create(platform, username)
        return profile.id

    async def test_unknown_id_returns_404(self, app: TestClient) -> None:
        response = app.patch(
            "/api/profiles/999",
            json={"is_primary": True},
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_update_username_only(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))

        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"username": "AliceCarlsen"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["username"] == "alicecarlsen"
        assert body["is_primary"] is True
        assert body["last_validated_at"] is not None

    async def test_update_is_primary_demotes_other(
        self,
        app: TestClient,
        db_path: Path,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            first = await repo.create("lichess", "alice")
            second = await repo.create("lichess", "bob")
        assert second.is_primary is False

        response = app.patch(
            f"/api/profiles/{second.id}",
            json={"is_primary": True},
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()["is_primary"] is True

        first_after = app.get("/api/profiles").json()["profiles"]
        first_record = next(p for p in first_after if p["id"] == first.id)
        assert first_record["is_primary"] is False

    async def test_update_preferences_only_leaves_identity(
        self,
        app: TestClient,
        db_path: Path,
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={
                "preferences": {
                    "auto_sync_enabled": False,
                    "sync_max_games": 50,
                }
            },
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["username"] == "alice"
        assert body["preferences"] == {
            "auto_sync_enabled": False,
            "sync_max_games": 50,
        }

    async def test_sync_max_games_null_clears_to_use_global(
        self,
        app: TestClient,
        db_path: Path,
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        # First set a value.
        app.patch(
            f"/api/profiles/{profile_id}",
            json={"preferences": {"sync_max_games": 50}},
        )
        # Then clear via explicit null.
        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"preferences": {"sync_max_games": None}},
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()["preferences"]["sync_max_games"] is None

    async def test_username_change_to_other_tracked_returns_409(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            await repo.create("lichess", "alice")
            second = await repo.create("lichess", "bob")
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))

        response = app.patch(
            f"/api/profiles/{second.id}",
            json={"username": "alice"},
        )
        assert response.status_code == HTTPStatus.CONFLICT

    async def test_username_change_to_nonexistent_is_accepted(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Spec judgment call: a non-existent target is accepted (the user may
        # be correcting a typo on a profile that's now invalid).
        profile_id = await self._create(db_path, "lichess", "alice")
        _patch_existence(monkeypatch, ExistenceCheck(exists=False, rate_limited=False))

        before = app.get("/api/profiles").json()["profiles"][0]
        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"username": "ghostuser"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["username"] == "ghostuser"
        # last_validated_at not advanced — we couldn't confirm existence.
        assert body["last_validated_at"] == before["last_validated_at"]

    async def test_empty_body_is_noop(
        self,
        app: TestClient,
        db_path: Path,
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.patch(f"/api/profiles/{profile_id}", json={})
        assert response.status_code == HTTPStatus.OK
        assert response.json()["username"] == "alice"

    async def test_explicit_null_username_returns_422(
        self, app: TestClient, db_path: Path
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"username": None},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_explicit_null_is_primary_returns_422(
        self, app: TestClient, db_path: Path
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"is_primary": None},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_explicit_null_auto_sync_enabled_returns_422(
        self, app: TestClient, db_path: Path
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"preferences": {"auto_sync_enabled": None}},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_upstream_error_accepts_change_without_validation(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        before = app.get("/api/profiles").json()["profiles"][0]

        response_500 = MagicMock()
        response_500.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        _patch_existence_raising(monkeypatch, RetryableHTTPError(response_500))

        response = app.patch(
            f"/api/profiles/{profile_id}",
            json={"username": "newname"},
        )
        # PATCH accepts the change but doesn't refresh last_validated_at —
        # we couldn't verify, so the timestamp stays put.
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["username"] == "newname"
        assert body["last_validated_at"] == before["last_validated_at"]


class TestDeleteProfile:
    async def _create(self, db_path: Path, platform: str, username: str) -> int:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create(platform, username)
        return profile.id

    def _insert_game_for(self, db_path: Path, *, game_id: str, profile_id: int) -> None:
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.execute(
                "INSERT INTO game_index_cache "
                "(game_id, source, username, pgn_content, indexed_at, profile_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (game_id, "lichess", "alice", "1.e4 e5", "2026-04-30", profile_id),
            )
            conn.commit()

    async def test_missing_detach_games_returns_400(
        self, app: TestClient, db_path: Path
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.delete(f"/api/profiles/{profile_id}")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    async def test_invalid_detach_games_returns_400(
        self, app: TestClient, db_path: Path
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        response = app.delete(f"/api/profiles/{profile_id}?detach_games=maybe")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_unknown_profile_returns_404(self, app: TestClient) -> None:
        response = app.delete("/api/profiles/999?detach_games=true")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_detach_keeps_games_with_null_profile_id(
        self, app: TestClient, db_path: Path
    ) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        self._insert_game_for(db_path, game_id="g1", profile_id=profile_id)

        response = app.delete(f"/api/profiles/{profile_id}?detach_games=true")
        assert response.status_code == HTTPStatus.NO_CONTENT

        with closing(sqlite3.connect(str(db_path))) as conn:
            game_row = conn.execute(
                "SELECT profile_id FROM game_index_cache WHERE game_id = 'g1'"
            ).fetchone()
            profile_row = conn.execute(
                "SELECT 1 FROM profile WHERE id = ?", (profile_id,)
            ).fetchone()
            prefs_row = conn.execute(
                "SELECT 1 FROM profile_preferences WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        assert game_row is not None
        assert game_row[0] is None
        assert profile_row is None
        assert prefs_row is None

    async def test_cascade_removes_games(self, app: TestClient, db_path: Path) -> None:
        profile_id = await self._create(db_path, "lichess", "alice")
        self._insert_game_for(db_path, game_id="g1", profile_id=profile_id)

        response = app.delete(f"/api/profiles/{profile_id}?detach_games=false")
        assert response.status_code == HTTPStatus.NO_CONTENT

        with closing(sqlite3.connect(str(db_path))) as conn:
            game_row = conn.execute(
                "SELECT 1 FROM game_index_cache WHERE game_id = 'g1'"
            ).fetchone()
        assert game_row is None

    async def test_deleting_primary_does_not_auto_promote_other(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            primary = await repo.create("lichess", "alice")
            secondary = await repo.create("lichess", "bob")
        assert primary.is_primary
        assert not secondary.is_primary

        response = app.delete(f"/api/profiles/{primary.id}?detach_games=true")
        assert response.status_code == HTTPStatus.NO_CONTENT

        listing = app.get("/api/profiles").json()["profiles"]
        assert len(listing) == 1
        assert listing[0]["id"] == secondary.id
        assert listing[0]["is_primary"] is False


def _patch_stats_fetcher(
    monkeypatch: pytest.MonkeyPatch, snapshots: list[ProfileStatSnapshot]
) -> None:
    async def _lichess(_username: str) -> list[ProfileStatSnapshot]:
        return snapshots

    async def _chesscom(_username: str) -> list[ProfileStatSnapshot]:
        return snapshots

    monkeypatch.setattr(
        "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
        _lichess,
    )
    monkeypatch.setattr(
        "blunder_tutor.background.jobs.stats_sync.chesscom.fetch_user_stats",
        _chesscom,
    )


def _patch_stats_fetcher_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise(_username: str) -> list[ProfileStatSnapshot]:
        raise RateLimitError("lichess")

    monkeypatch.setattr(
        "blunder_tutor.background.jobs.stats_sync.lichess.fetch_user_perfs",
        _raise,
    )


class TestProfileSyncEndpoint:
    async def test_post_sync_returns_job_id_and_publishes_event(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        bus = app.app.state.event_bus
        queue = await bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

        response = app.post(f"/api/profiles/{profile.id}/sync")

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["job_id"]

        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event.data["job_type"] == JOB_TYPE_IMPORT
        assert event.data["job_id"] == body["job_id"]
        assert event.data["kwargs"]["profile_id"] == profile.id

    def test_post_sync_unknown_profile_returns_404(self, app: TestClient) -> None:
        response = app.post("/api/profiles/9999/sync")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestProfileStatsRefreshEndpoint:
    async def test_post_refresh_returns_refreshed_stats(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        snapshots = [
            ProfileStatSnapshot(mode="bullet", rating=2400, games_count=1500),
            ProfileStatSnapshot(mode="blitz", rating=2300, games_count=900),
        ]
        _patch_stats_fetcher(monkeypatch, snapshots)

        response = app.post(f"/api/profiles/{profile.id}/stats/refresh")

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        # Repo lists stats ordered by mode → blitz, bullet alphabetic.
        modes = [stat["mode"] for stat in body["stats"]]
        assert sorted(modes) == ["blitz", "bullet"]
        ratings = {stat["mode"]: stat["rating"] for stat in body["stats"]}
        assert ratings == {"bullet": 2400, "blitz": 2300}
        assert body["last_validated_at"] is not None

    async def test_post_refresh_rate_limited_returns_429(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        _patch_stats_fetcher_rate_limit(monkeypatch)

        response = app.post(f"/api/profiles/{profile.id}/stats/refresh")

        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        body = response.json()
        # FastAPI wraps the dict detail under `detail`.
        assert body["detail"]["rate_limited"] is True

    async def test_post_refresh_does_not_touch_validated_at_on_rate_limit(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        _patch_stats_fetcher_rate_limit(monkeypatch)

        app.post(f"/api/profiles/{profile.id}/stats/refresh")

        # `last_validated_at` is the freshness signal — must NOT advance
        # when the upstream couldn't be reached.
        with closing(sqlite3.connect(str(db_path))) as conn:
            row = conn.execute(
                "SELECT last_validated_at FROM profile WHERE id = ?",
                (profile.id,),
            ).fetchone()
        assert row[0] is None

    def test_post_refresh_unknown_profile_returns_404(self, app: TestClient) -> None:
        response = app.post("/api/profiles/9999/stats/refresh")
        assert response.status_code == HTTPStatus.NOT_FOUND
