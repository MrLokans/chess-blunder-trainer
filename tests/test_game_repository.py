"""Tests for GameRepository."""

from __future__ import annotations

import chess.pgn
import pytest

from blunder_tutor.repositories.game_repository import GameRepository

SAMPLE_GAME = {
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
}


def _game(**overrides: object) -> dict[str, object]:
    g = {**SAMPLE_GAME, **overrides}
    return g


class TestGetLatestGameTime:
    async def test_returns_none_when_no_games(self, game_repo: GameRepository):
        result = await game_repo.get_latest_game_time("lichess", "testuser")
        assert result is None

    async def test_returns_latest_game_time(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="game1", end_time_utc="2024-01-10T12:00:00+00:00"),
                _game(
                    id="game2",
                    end_time_utc="2024-01-15T14:30:00+00:00",
                    date="2024.01.15",
                ),
            ]
        )
        result = await game_repo.get_latest_game_time("lichess", "testuser")
        assert result is not None
        assert result.day == 15

    async def test_filters_by_source(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(
                    id="lg", source="lichess", end_time_utc="2024-01-10T12:00:00+00:00"
                ),
                _game(
                    id="cg", source="chesscom", end_time_utc="2024-01-20T12:00:00+00:00"
                ),
            ]
        )
        assert (await game_repo.get_latest_game_time("lichess", "testuser")).day == 10
        assert (await game_repo.get_latest_game_time("chesscom", "testuser")).day == 20

    async def test_filters_by_username(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="u1g", username="user1", white="user1"),
                _game(
                    id="u2g",
                    username="user2",
                    white="user2",
                    end_time_utc="2024-01-20T12:00:00+00:00",
                ),
            ]
        )
        assert (await game_repo.get_latest_game_time("lichess", "user1")).day == 10
        assert (await game_repo.get_latest_game_time("lichess", "user2")).day == 20


class TestInsertAndListGames:
    async def test_insert_returns_count(self, game_repo: GameRepository):
        count = await game_repo.insert_games([_game(), _game(id="game2")])
        assert count == 2

    async def test_duplicate_insert_ignored(self, game_repo: GameRepository):
        await game_repo.insert_games([_game()])
        count = await game_repo.insert_games([_game()])
        assert count == 0

    async def test_list_games_returns_all(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1"), _game(id="g2")])
        games = [g async for g in game_repo.list_games()]
        assert len(games) == 2

    async def test_list_games_source_filter(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", source="lichess"),
                _game(id="g2", source="chesscom"),
            ]
        )
        games = [g async for g in game_repo.list_games(source="lichess")]
        assert len(games) == 1
        assert games[0]["source"] == "lichess"

    async def test_list_games_username_filter(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", username="alice"),
                _game(id="g2", username="bob"),
            ]
        )
        games = [g async for g in game_repo.list_games(username="alice")]
        assert len(games) == 1
        assert games[0]["username"] == "alice"

    async def test_list_games_limit(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id=f"g{i}") for i in range(5)])
        games = [g async for g in game_repo.list_games(limit=2)]
        assert len(games) == 2


class TestGetAllGameSideMap:
    async def test_white_player(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [_game(id="g1", username="testuser", white="testuser")]
        )
        result = await game_repo.get_all_game_side_map()
        assert result["g1"] == 0

    async def test_black_player(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", username="testuser", white="opponent", black="testuser"),
            ]
        )
        result = await game_repo.get_all_game_side_map()
        assert result["g1"] == 1

    async def test_no_username_skipped(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1", username="")])
        result = await game_repo.get_all_game_side_map()
        assert "g1" not in result


class TestGetPgnContentAndLoadGame:
    async def test_get_pgn_content(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1")])
        pgn = await game_repo.get_pgn_content("g1")
        assert pgn == SAMPLE_GAME["pgn_content"]

    async def test_get_pgn_content_not_found(self, game_repo: GameRepository):
        with pytest.raises(FileNotFoundError):
            await game_repo.get_pgn_content("nonexistent")

    async def test_load_game(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1")])
        game = await game_repo.load_game("g1")
        assert isinstance(game, chess.pgn.Game)


class TestGetGame:
    async def test_found(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1")])
        result = await game_repo.get_game("g1")
        assert result is not None
        assert result["id"] == "g1"
        assert result["white"] == "testuser"
        assert result["pgn_content"] == SAMPLE_GAME["pgn_content"]

    async def test_not_found(self, game_repo: GameRepository):
        result = await game_repo.get_game("nonexistent")
        assert result is None


class TestListGamesFiltered:
    async def _seed(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", source="lichess", end_time_utc="2024-01-10T12:00:00"),
                _game(id="g2", source="chesscom", end_time_utc="2024-02-15T12:00:00"),
                _game(id="g3", source="lichess", end_time_utc="2024-03-20T12:00:00"),
            ]
        )
        await game_repo.mark_game_analyzed("g1")

    async def test_no_filters(self, game_repo: GameRepository):
        await self._seed(game_repo)
        games, total = await game_repo.list_games_filtered()
        assert total == 3
        assert len(games) == 3

    async def test_source_filter(self, game_repo: GameRepository):
        await self._seed(game_repo)
        games, total = await game_repo.list_games_filtered(source="lichess")
        assert total == 2

    async def test_username_filter(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", username="alice"),
                _game(id="g2", username="bob"),
            ]
        )
        games, total = await game_repo.list_games_filtered(username="alice")
        assert total == 1

    async def test_date_range(self, game_repo: GameRepository):
        await self._seed(game_repo)
        games, total = await game_repo.list_games_filtered(
            start_date="2024-02-01", end_date="2024-03-01"
        )
        assert total == 1
        assert games[0]["id"] == "g2"

    async def test_analyzed_only(self, game_repo: GameRepository):
        await self._seed(game_repo)
        games, total = await game_repo.list_games_filtered(analyzed_only=True)
        assert total == 1
        assert games[0]["id"] == "g1"

    async def test_pagination(self, game_repo: GameRepository):
        await self._seed(game_repo)
        games, total = await game_repo.list_games_filtered(limit=1, offset=0)
        assert total == 3
        assert len(games) == 1
        games2, _ = await game_repo.list_games_filtered(limit=1, offset=1)
        assert len(games2) == 1
        assert games[0]["id"] != games2[0]["id"]


class TestCountGames:
    async def test_empty(self, game_repo: GameRepository):
        assert await game_repo.count_games() == 0

    async def test_counts_all(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1"), _game(id="g2")])
        assert await game_repo.count_games() == 2

    async def test_source_filter(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", source="lichess"),
                _game(id="g2", source="chesscom"),
            ]
        )
        assert await game_repo.count_games(source="lichess") == 1

    async def test_analyzed_only(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1"), _game(id="g2")])
        await game_repo.mark_game_analyzed("g1")
        assert await game_repo.count_games(analyzed_only=True) == 1

    async def test_username_filter(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", username="alice"),
                _game(id="g2", username="bob"),
            ]
        )
        assert await game_repo.count_games(username="alice") == 1

    async def test_date_range(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", end_time_utc="2024-01-10T12:00:00"),
                _game(id="g2", end_time_utc="2024-06-10T12:00:00"),
            ]
        )
        assert await game_repo.count_games(start_date="2024-05-01") == 1
        assert await game_repo.count_games(end_date="2024-03-01") == 1


class TestMarkGameAnalyzedAndUnanalyzed:
    async def test_mark_analyzed(self, game_repo: GameRepository):
        await game_repo.insert_games([_game(id="g1")])
        unanalyzed = await game_repo.list_unanalyzed_game_ids()
        assert "g1" in unanalyzed

        await game_repo.mark_game_analyzed("g1")
        unanalyzed = await game_repo.list_unanalyzed_game_ids()
        assert "g1" not in unanalyzed

    async def test_list_unanalyzed_filters(self, game_repo: GameRepository):
        await game_repo.insert_games(
            [
                _game(id="g1", source="lichess", username="alice"),
                _game(id="g2", source="chesscom", username="bob"),
            ]
        )
        ids = await game_repo.list_unanalyzed_game_ids(source="lichess")
        assert ids == ["g1"]

        ids = await game_repo.list_unanalyzed_game_ids(username="bob")
        assert ids == ["g2"]
