from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator
from contextlib import closing
from pathlib import Path

import pytest

from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.repositories.profile_types import ProfileNotFoundError
from blunder_tutor.services.rating_history import RatingHistoryService
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
    profile_id: int | None,
    username: str,
    white: str,
    black: str,
    white_elo: int | str = "?",
    black_elo: int | str = "?",
    end_time_utc: str = "2026-01-01T00:00:00",
    game_type: int = int(GameType.BLITZ),
    time_control: str = "300",
) -> None:
    pgn = _make_pgn(white=white, black=black, white_elo=white_elo, black_elo=black_elo)
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO game_index_cache "
            "(game_id, source, username, white, black, "
            " result, date, end_time_utc, time_control, "
            " pgn_content, indexed_at, game_type, profile_id) "
            "VALUES (?, 'lichess', ?, ?, ?, '*', '2026-01-01', "
            "        ?, ?, ?, '2026-01-01', ?, ?)",
            (
                game_id,
                username,
                white,
                black,
                end_time_utc,
                time_control,
                pgn,
                game_type,
                profile_id,
            ),
        )
        conn.commit()


@pytest.fixture
async def profile_repo(db_path: Path) -> AsyncGenerator[SqliteProfileRepository]:
    repo = SqliteProfileRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def game_repo(db_path: Path) -> AsyncGenerator[GameRepository]:
    repo = GameRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def service(
    profile_repo: SqliteProfileRepository, game_repo: GameRepository
) -> RatingHistoryService:
    return RatingHistoryService(profiles=profile_repo, games=game_repo)


class TestRatingHistoryService:
    async def test_unknown_profile_raises(self, service: RatingHistoryService) -> None:
        with pytest.raises(ProfileNotFoundError):
            await service.get(profile_id=9999)

    async def test_empty_history_when_no_games(
        self,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
        assert await service.get(profile_id=profile.id) == []

    async def test_picks_white_side_when_user_is_white(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
        _insert_game(
            db_path,
            game_id="g1",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo=1500,
            black_elo=1480,
        )

        points = await service.get(profile_id=profile.id)
        assert len(points) == 1
        assert points[0].rating == 1500
        assert points[0].color == "white"
        assert points[0].opponent_rating == 1480

    async def test_picks_black_side_when_user_is_black(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
        _insert_game(
            db_path,
            game_id="g1",
            profile_id=profile.id,
            username="alice",
            white="bob",
            black="alice",
            white_elo=1480,
            black_elo=1500,
        )

        points = await service.get(profile_id=profile.id)
        assert len(points) == 1
        assert points[0].rating == 1500
        assert points[0].color == "black"
        assert points[0].opponent_rating == 1480

    async def test_username_match_is_case_insensitive(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        # Profile stored lowercase by repo; PGN headers may have any case.
        profile = await profile_repo.create("lichess", "Alice")
        _insert_game(
            db_path,
            game_id="g1",
            profile_id=profile.id,
            username="alice",
            white="ALICE",
            black="Bob",
            white_elo=1500,
            black_elo=1480,
        )

        points = await service.get(profile_id=profile.id)
        assert len(points) == 1
        assert points[0].color == "white"

    async def test_results_sorted_ascending_by_time(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
        _insert_game(
            db_path,
            game_id="late",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo=1520,
            black_elo=1500,
            end_time_utc="2026-03-01T00:00:00",
        )
        _insert_game(
            db_path,
            game_id="early",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo=1500,
            black_elo=1500,
            end_time_utc="2026-01-01T00:00:00",
        )

        points = await service.get(profile_id=profile.id)
        assert [p.end_time_utc for p in points] == [
            "2026-01-01T00:00:00",
            "2026-03-01T00:00:00",
        ]

    async def test_skips_games_with_missing_user_side_elo(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
        # alice is white but WhiteElo is "?" — drop this row.
        _insert_game(
            db_path,
            game_id="missing",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo="?",
            black_elo=1480,
        )
        # alice is white with valid elo — keep.
        _insert_game(
            db_path,
            game_id="good",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo=1500,
            black_elo=1480,
            end_time_utc="2026-02-01T00:00:00",
        )

        points = await service.get(profile_id=profile.id)
        assert len(points) == 1
        assert points[0].rating == 1500

    async def test_skips_games_where_user_is_neither_color(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        # Defensive — should not normally happen if profile_id is set
        # correctly, but covers the case of a stale denormalized row.
        profile = await profile_repo.create("lichess", "alice")
        _insert_game(
            db_path,
            game_id="g1",
            profile_id=profile.id,
            username="alice",
            white="bob",
            black="charlie",
            white_elo=1500,
            black_elo=1480,
        )

        points = await service.get(profile_id=profile.id)
        assert points == []

    async def test_does_not_include_other_profiles_games(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        alice = await profile_repo.create("lichess", "alice")
        bob = await profile_repo.create("lichess", "bob")
        _insert_game(
            db_path,
            game_id="alice_game",
            profile_id=alice.id,
            username="alice",
            white="alice",
            black="x",
            white_elo=1500,
            black_elo=1500,
        )
        _insert_game(
            db_path,
            game_id="bob_game",
            profile_id=bob.id,
            username="bob",
            white="bob",
            black="y",
            white_elo=1700,
            black_elo=1700,
        )

        alice_points = await service.get(profile_id=alice.id)
        assert len(alice_points) == 1
        assert alice_points[0].rating == 1500

    async def test_filters_by_mode(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
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
            white_elo=1550,
            black_elo=1550,
            game_type=int(GameType.RAPID),
        )

        blitz = await service.get(profile_id=profile.id, mode="blitz")
        assert len(blitz) == 1
        assert blitz[0].rating == 1500
        assert blitz[0].game_type == "blitz"

        rapid = await service.get(profile_id=profile.id, mode="rapid")
        assert len(rapid) == 1
        assert rapid[0].rating == 1550

    async def test_filters_by_since_inclusive(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
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

        points = await service.get(profile_id=profile.id, since="2026-02-01T00:00:00")
        assert len(points) == 1
        assert points[0].rating == 1500

    async def test_unknown_mode_raises_value_error(
        self,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        profile = await profile_repo.create("lichess", "alice")
        with pytest.raises(ValueError):
            await service.get(profile_id=profile.id, mode="bogus")

    async def test_keeps_only_last_game_of_each_day(
        self,
        db_path: Path,
        profile_repo: SqliteProfileRepository,
        service: RatingHistoryService,
    ) -> None:
        # Three games on the same day with a rating climb. Daily bucket
        # should keep only the latest game (1530), not the earlier 1510 / 1520.
        profile = await profile_repo.create("lichess", "alice")
        for game_id, end_time, white_elo in (
            ("g_morning", "2026-04-15T08:00:00", 1510),
            ("g_noon", "2026-04-15T12:00:00", 1520),
            ("g_evening", "2026-04-15T20:00:00", 1530),
        ):
            _insert_game(
                db_path,
                game_id=game_id,
                profile_id=profile.id,
                username="alice",
                white="alice",
                black="bob",
                white_elo=white_elo,
                black_elo=1500,
                end_time_utc=end_time,
            )
        # And one game on a different day.
        _insert_game(
            db_path,
            game_id="next_day",
            profile_id=profile.id,
            username="alice",
            white="alice",
            black="bob",
            white_elo=1540,
            black_elo=1500,
            end_time_utc="2026-04-16T10:00:00",
        )

        points = await service.get(profile_id=profile.id)
        ratings = [p.rating for p in points]
        end_times = [p.end_time_utc for p in points]
        assert ratings == [1530, 1540]
        assert end_times == [
            "2026-04-15T20:00:00",
            "2026-04-16T10:00:00",
        ]
