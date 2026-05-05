from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.utils.time_control import GameType


def _days_ago(n: int) -> str:
    return (datetime.now(UTC) - timedelta(days=n)).isoformat()


def _make_pgn(
    *, white: str, black: str, white_elo: int | str, black_elo: int | str
) -> str:
    return (
        f'[White "{white}"]\n[Black "{black}"]\n'
        f'[WhiteElo "{white_elo}"]\n[BlackElo "{black_elo}"]\n'
        f'[Result "*"]\n\n*\n'
    )


def _insert_game(
    db: Path,
    *,
    game_id: str,
    profile_id: int,
    username: str,
    white: str,
    black: str,
    white_elo: int | str,
    black_elo: int | str,
    end_time_utc: str = "2026-01-01T00:00:00",
    game_type: int = int(GameType.BLITZ),
) -> None:
    pgn = _make_pgn(white=white, black=black, white_elo=white_elo, black_elo=black_elo)
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO game_index_cache "
            "(game_id, source, username, white, black, "
            " result, date, end_time_utc, time_control, "
            " pgn_content, indexed_at, game_type, profile_id) "
            "VALUES (?, 'lichess', ?, ?, ?, '*', '2026-01-01', "
            "        ?, '300', ?, '2026-01-01', ?, ?)",
            (
                game_id,
                username,
                white,
                black,
                end_time_utc,
                pgn,
                game_type,
                profile_id,
            ),
        )
        conn.commit()


class TestRatingHistoryEndpoint:
    async def test_happy_path(self, app: TestClient, db_path: Path) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        _insert_game(
            db_path,
            game_id="g1",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo=1500,
            black_elo=1480,
            end_time_utc=_days_ago(10),
        )
        _insert_game(
            db_path,
            game_id="g2",
            profile_id=profile.id,
            username="alice",
            white="bob",
            black="alice",
            white_elo=1520,
            black_elo=1510,
            end_time_utc=_days_ago(2),
        )

        response = app.get(f"/api/profiles/{profile.id}/rating-history")
        assert response.status_code == HTTPStatus.OK

        body = response.json()
        points = body["points"]
        assert len(points) == 2
        assert points[0]["rating"] == 1500
        assert points[0]["color"] == "white"
        assert points[0]["opponent_rating"] == 1480
        assert points[0]["game_type"] == "blitz"
        assert points[1]["rating"] == 1510
        assert points[1]["color"] == "black"

    def test_unknown_profile_returns_404(self, app: TestClient) -> None:
        response = app.get("/api/profiles/9999/rating-history")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_unknown_mode_returns_422(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        response = app.get(f"/api/profiles/{profile.id}/rating-history?mode=bogus")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT

    async def test_mode_filter_narrows_results(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        _insert_game(
            db_path,
            game_id="blitz_game",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1500,
            black_elo=1500,
            end_time_utc=_days_ago(3),
            game_type=int(GameType.BLITZ),
        )
        _insert_game(
            db_path,
            game_id="rapid_game",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1600,
            black_elo=1600,
            end_time_utc=_days_ago(3),
            game_type=int(GameType.RAPID),
        )

        response = app.get(f"/api/profiles/{profile.id}/rating-history?mode=rapid")
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert len(body["points"]) == 1
        assert body["points"][0]["rating"] == 1600
        assert body["points"][0]["game_type"] == "rapid"

    async def test_excludes_games_older_than_30_days(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        # Two days old → in window. 35 days old → excluded.
        _insert_game(
            db_path,
            game_id="recent",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1500,
            black_elo=1500,
            end_time_utc=_days_ago(2),
        )
        _insert_game(
            db_path,
            game_id="ancient",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1100,
            black_elo=1100,
            end_time_utc=_days_ago(35),
        )

        response = app.get(f"/api/profiles/{profile.id}/rating-history")
        body = response.json()
        ratings = [p["rating"] for p in body["points"]]
        assert ratings == [1500]

    async def test_buckets_to_one_point_per_day(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        # Three games on the same day; only the latest survives.
        same_day = datetime.now(UTC) - timedelta(days=1)
        for game_id, hours, white_elo in (
            ("morning", 8, 1510),
            ("noon", 12, 1520),
            ("evening", 20, 1530),
        ):
            _insert_game(
                db_path,
                game_id=game_id,
                profile_id=profile.id,
                username="alice",
                white="alice",
                black="x",
                white_elo=white_elo,
                black_elo=1500,
                end_time_utc=same_day.replace(
                    hour=hours, minute=0, second=0, microsecond=0
                ).isoformat(),
            )

        response = app.get(f"/api/profiles/{profile.id}/rating-history")
        body = response.json()
        ratings = [p["rating"] for p in body["points"]]
        assert ratings == [1530]
