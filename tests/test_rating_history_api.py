from __future__ import annotations

import sqlite3
from contextlib import closing
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.utils.time_control import GameType


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
            end_time_utc="2026-01-01T00:00:00",
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
            end_time_utc="2026-02-01T00:00:00",
        )

        response = app.get(f"/api/profiles/{profile.id}/rating-history")
        assert response.status_code == HTTPStatus.OK

        body = response.json()
        points = body["points"]
        assert len(points) == 2
        assert [p["end_time_utc"] for p in points] == [
            "2026-01-01T00:00:00",
            "2026-02-01T00:00:00",
        ]
        assert points[0] == {
            "end_time_utc": "2026-01-01T00:00:00",
            "rating": 1500,
            "game_type": "blitz",
            "color": "white",
            "opponent_rating": 1480,
        }
        assert points[1]["color"] == "black"
        assert points[1]["rating"] == 1510

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
            game_type=int(GameType.RAPID),
        )

        response = app.get(f"/api/profiles/{profile.id}/rating-history?mode=rapid")
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert len(body["points"]) == 1
        assert body["points"][0]["rating"] == 1600
        assert body["points"][0]["game_type"] == "rapid"

    async def test_since_filter(self, app: TestClient, db_path: Path) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        _insert_game(
            db_path,
            game_id="old",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1400,
            black_elo=1400,
            end_time_utc="2026-01-01T00:00:00",
        )
        _insert_game(
            db_path,
            game_id="new",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1500,
            black_elo=1500,
            end_time_utc="2026-03-01T00:00:00",
        )

        response = app.get(
            f"/api/profiles/{profile.id}/rating-history?since=2026-02-01T00:00:00"
        )
        body = response.json()
        assert len(body["points"]) == 1
        assert body["points"][0]["rating"] == 1500
