"""Tests for GameRepository."""

from __future__ import annotations

from blunder_tutor.repositories.game_repository import GameRepository


class TestGetLatestGameTime:
    async def test_returns_none_when_no_games(self, game_repo: GameRepository):
        result = await game_repo.get_latest_game_time("lichess", "testuser")
        assert result is None

    async def test_returns_latest_game_time(self, game_repo: GameRepository):
        games = [
            {
                "id": "game1",
                "source": "lichess",
                "username": "testuser",
                "white": "testuser",
                "black": "opponent",
                "result": "1-0",
                "date": "2024.01.10",
                "end_time_utc": "2024-01-10T12:00:00+00:00",
                "time_control": "180+0",
                "pgn_content": '[Event "Test"]\n1. e4 e5 1-0',
            },
            {
                "id": "game2",
                "source": "lichess",
                "username": "testuser",
                "white": "opponent",
                "black": "testuser",
                "result": "0-1",
                "date": "2024.01.15",
                "end_time_utc": "2024-01-15T14:30:00+00:00",
                "time_control": "180+0",
                "pgn_content": '[Event "Test"]\n1. d4 d5 0-1',
            },
        ]
        await game_repo.insert_games(games)

        result = await game_repo.get_latest_game_time("lichess", "testuser")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    async def test_filters_by_source(self, game_repo: GameRepository):
        games = [
            {
                "id": "lichess_game",
                "source": "lichess",
                "username": "testuser",
                "white": "testuser",
                "black": "opponent",
                "result": "1-0",
                "date": "2024.01.10",
                "end_time_utc": "2024-01-10T12:00:00+00:00",
                "time_control": "180+0",
                "pgn_content": '[Event "Test"]\n1. e4 e5 1-0',
            },
            {
                "id": "chesscom_game",
                "source": "chesscom",
                "username": "testuser",
                "white": "testuser",
                "black": "opponent",
                "result": "1-0",
                "date": "2024.01.20",
                "end_time_utc": "2024-01-20T12:00:00+00:00",
                "time_control": "180+0",
                "pgn_content": '[Event "Test"]\n1. e4 e5 1-0',
            },
        ]
        await game_repo.insert_games(games)

        lichess_result = await game_repo.get_latest_game_time("lichess", "testuser")
        chesscom_result = await game_repo.get_latest_game_time("chesscom", "testuser")

        assert lichess_result is not None
        assert lichess_result.day == 10
        assert chesscom_result is not None
        assert chesscom_result.day == 20

    async def test_filters_by_username(self, game_repo: GameRepository):
        games = [
            {
                "id": "user1_game",
                "source": "lichess",
                "username": "user1",
                "white": "user1",
                "black": "opponent",
                "result": "1-0",
                "date": "2024.01.10",
                "end_time_utc": "2024-01-10T12:00:00+00:00",
                "time_control": "180+0",
                "pgn_content": '[Event "Test"]\n1. e4 e5 1-0',
            },
            {
                "id": "user2_game",
                "source": "lichess",
                "username": "user2",
                "white": "user2",
                "black": "opponent",
                "result": "1-0",
                "date": "2024.01.20",
                "end_time_utc": "2024-01-20T12:00:00+00:00",
                "time_control": "180+0",
                "pgn_content": '[Event "Test"]\n1. e4 e5 1-0',
            },
        ]
        await game_repo.insert_games(games)

        user1_result = await game_repo.get_latest_game_time("lichess", "user1")
        user2_result = await game_repo.get_latest_game_time("lichess", "user2")

        assert user1_result is not None
        assert user1_result.day == 10
        assert user2_result is not None
        assert user2_result.day == 20
