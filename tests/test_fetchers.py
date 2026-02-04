from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from hyx.retry.exceptions import MaxAttemptsExceeded

from blunder_tutor.fetchers import chesscom, lichess
from blunder_tutor.fetchers.resilience import RetryableHTTPError, fetch_with_retry

SAMPLE_PGN_1 = """[Event "Rated Blitz game"]
[Site "https://lichess.org/abcd1234"]
[Date "2024.01.15"]
[White "player1"]
[Black "player2"]
[Result "1-0"]
[UTCDate "2024.01.15"]
[UTCTime "12:30:00"]
[WhiteElo "1500"]
[BlackElo "1400"]
[TimeControl "180+0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

SAMPLE_PGN_2 = """[Event "Rated Blitz game"]
[Site "https://lichess.org/efgh5678"]
[Date "2024.01.14"]
[White "player2"]
[Black "player1"]
[Result "0-1"]
[UTCDate "2024.01.14"]
[UTCTime "10:00:00"]
[WhiteElo "1400"]
[BlackElo "1500"]
[TimeControl "180+0"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 0-1
"""

SAMPLE_PGN_3 = """[Event "Rated Rapid game"]
[Site "https://lichess.org/ijkl9012"]
[Date "2024.01.13"]
[White "player1"]
[Black "player3"]
[Result "1/2-1/2"]
[UTCDate "2024.01.13"]
[UTCTime "08:00:00"]
[WhiteElo "1500"]
[BlackElo "1600"]
[TimeControl "600+0"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 1/2-1/2
"""


def create_mock_response(
    status_code: int = 200,
    text: str | None = None,
    json_data: dict[str, Any] | None = None,
) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text or ""
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=response
        )
    if json_data is not None:
        response.json = MagicMock(return_value=json_data)
    return response


def create_mock_client(
    handler: Any,
) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(side_effect=lambda url, **kwargs: handler(str(url)))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def create_single_response_handler(
    response_text: str = "",
    json_data: dict[str, Any] | None = None,
) -> Any:
    call_count = 0

    def handler(url: str) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            if json_data is not None:
                return create_mock_response(json_data=json_data)
            return create_mock_response(text=response_text)
        return create_mock_response(text="")

    return handler


class TestLichessFetch:
    async def test_fetch_single_batch(self, monkeypatch: pytest.MonkeyPatch):
        pgn_response = SAMPLE_PGN_1 + "\n" + SAMPLE_PGN_2

        handler = create_single_response_handler(response_text=pgn_response)
        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await lichess.fetch("testuser", max_games=10)

        assert len(games) == 2
        assert len(seen_ids) == 2
        assert games[0]["source"] == "lichess"
        assert games[0]["username"] == "testuser"

    async def test_fetch_respects_max_games(self, monkeypatch: pytest.MonkeyPatch):
        pgn_response = SAMPLE_PGN_1 + "\n" + SAMPLE_PGN_2 + "\n" + SAMPLE_PGN_3

        def handler(url: str) -> MagicMock:
            return create_mock_response(text=pgn_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await lichess.fetch("testuser", max_games=2)

        assert len(games) == 2

    async def test_progress_callback_called(self, monkeypatch: pytest.MonkeyPatch):
        pgn_response = SAMPLE_PGN_1 + "\n" + SAMPLE_PGN_2

        handler = create_single_response_handler(response_text=pgn_response)
        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await lichess.fetch(
            "testuser", max_games=10, progress_callback=progress_callback
        )

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 1
        assert callback_calls[1][0] == 2

    async def test_progress_callback_with_max_games(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        pgn_response = SAMPLE_PGN_1 + "\n" + SAMPLE_PGN_2 + "\n" + SAMPLE_PGN_3

        def handler(url: str) -> MagicMock:
            return create_mock_response(text=pgn_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await lichess.fetch(
            "testuser", max_games=3, progress_callback=progress_callback
        )

        assert len(callback_calls) == 3
        for current, total in callback_calls:
            assert total == 3

    async def test_empty_response(self, monkeypatch: pytest.MonkeyPatch):
        def handler(url: str) -> MagicMock:
            return create_mock_response(text="")

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await lichess.fetch("testuser")

        assert len(games) == 0
        assert len(seen_ids) == 0

    async def test_http_error_propagates(self, monkeypatch: pytest.MonkeyPatch):
        def handler(url: str) -> MagicMock:
            return create_mock_response(status_code=404, text="Not found")

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            await lichess.fetch("nonexistent_user")


class TestChesscomFetch:
    async def test_fetch_single_archive(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_1},
                {"pgn": SAMPLE_PGN_2},
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await chesscom.fetch("testuser")

        assert len(games) == 2
        assert len(seen_ids) == 2
        assert games[0]["source"] == "chesscom"
        assert games[0]["username"] == "testuser"

    async def test_fetch_multiple_archives(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {
            "archives": [
                "https://api.chess.com/pub/player/test/games/2024/01",
                "https://api.chess.com/pub/player/test/games/2024/02",
            ]
        }
        games_jan = {"games": [{"pgn": SAMPLE_PGN_1}]}
        games_feb = {"games": [{"pgn": SAMPLE_PGN_2}]}

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            if "2024/01" in url:
                return create_mock_response(json_data=games_jan)
            if "2024/02" in url:
                return create_mock_response(json_data=games_feb)
            return create_mock_response(status_code=404)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await chesscom.fetch("testuser")

        assert len(games) == 2
        assert len(seen_ids) == 2

    async def test_fetch_respects_max_games(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_1},
                {"pgn": SAMPLE_PGN_2},
                {"pgn": SAMPLE_PGN_3},
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await chesscom.fetch("testuser", max_games=2)

        assert len(games) == 2

    async def test_progress_callback_called(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_1},
                {"pgn": SAMPLE_PGN_2},
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await chesscom.fetch(
            "testuser", max_games=10, progress_callback=progress_callback
        )

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 1
        assert callback_calls[1][0] == 2

    async def test_progress_callback_with_max_games(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_1},
                {"pgn": SAMPLE_PGN_2},
                {"pgn": SAMPLE_PGN_3},
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await chesscom.fetch(
            "testuser", max_games=3, progress_callback=progress_callback
        )

        assert len(callback_calls) == 3
        for current, total in callback_calls:
            assert total == 3

    async def test_empty_archives(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {"archives": []}

        def handler(url: str) -> MagicMock:
            return create_mock_response(json_data=archives_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await chesscom.fetch("testuser")

        assert len(games) == 0
        assert len(seen_ids) == 0

    async def test_games_without_pgn_skipped(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_1},
                {"url": "some_game_without_pgn"},
                {"pgn": None},
                {"pgn": ""},
                {"pgn": SAMPLE_PGN_2},
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, seen_ids = await chesscom.fetch("testuser")

        assert len(games) == 2

    async def test_http_error_propagates(self, monkeypatch: pytest.MonkeyPatch):
        def handler(url: str) -> MagicMock:
            return create_mock_response(status_code=404, text="Not found")

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            await chesscom.fetch("nonexistent_user")

    async def test_username_lowercased(self, monkeypatch: pytest.MonkeyPatch):
        archives_response = {"archives": []}
        captured_urls: list[str] = []

        def handler(url: str) -> MagicMock:
            captured_urls.append(url)
            return create_mock_response(json_data=archives_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        await chesscom.fetch("TestUser")

        assert "testuser" in captured_urls[0]
        assert "TestUser" not in captured_urls[0]

    async def test_max_games_returns_most_recent(self, monkeypatch: pytest.MonkeyPatch):
        """With max_games, should return the most recent games, not oldest."""
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        # Games ordered oldest to newest (as Chess.com API returns them)
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_3},  # 2024.01.13 - oldest
                {"pgn": SAMPLE_PGN_2},  # 2024.01.14
                {"pgn": SAMPLE_PGN_1},  # 2024.01.15 - newest
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, _ = await chesscom.fetch("testuser", max_games=1)

        assert len(games) == 1
        # Should get the newest game (2024.01.15), not the oldest
        assert games[0]["date"] == "2024.01.15"


class TestProgressCallbackBehavior:
    async def test_lichess_callback_increments_correctly(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        pgn_response = SAMPLE_PGN_1 + "\n" + SAMPLE_PGN_2 + "\n" + SAMPLE_PGN_3

        def handler(url: str) -> MagicMock:
            return create_mock_response(text=pgn_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await lichess.fetch(
            "testuser", max_games=3, progress_callback=progress_callback
        )

        currents = [c for c, _ in callback_calls]
        assert currents == [1, 2, 3]

    async def test_chesscom_callback_increments_correctly(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        games_response = {
            "games": [
                {"pgn": SAMPLE_PGN_1},
                {"pgn": SAMPLE_PGN_2},
                {"pgn": SAMPLE_PGN_3},
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await chesscom.fetch(
            "testuser", max_games=3, progress_callback=progress_callback
        )

        currents = [c for c, _ in callback_calls]
        assert currents == [1, 2, 3]

    async def test_callback_not_called_when_none(self, monkeypatch: pytest.MonkeyPatch):
        pgn_response = SAMPLE_PGN_1

        handler = create_single_response_handler(response_text=pgn_response)
        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        games, _ = await lichess.fetch("testuser", progress_callback=None)

        assert len(games) == 1

    async def test_callback_total_equals_max_games_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        pgn_response = SAMPLE_PGN_1 + "\n" + SAMPLE_PGN_2

        def handler(url: str) -> MagicMock:
            return create_mock_response(text=pgn_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        callback_calls: list[tuple[int, int]] = []

        async def progress_callback(current: int, total: int) -> None:
            callback_calls.append((current, total))

        await lichess.fetch(
            "testuser", max_games=2, progress_callback=progress_callback
        )

        for current, total in callback_calls:
            assert total == 2


class TestIncrementalFetch:
    async def test_lichess_since_parameter_passed(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that since parameter is converted to milliseconds and passed to API."""
        from datetime import UTC, datetime

        captured_params: list[dict] = []

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            captured_params.append(kwargs.get("params", {}))
            return create_mock_response(text="")

        client = MagicMock()
        client.get = mock_get
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        since_dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        await lichess.fetch("testuser", since=since_dt)

        assert len(captured_params) > 0
        assert "since" in captured_params[0]
        expected_ms = int(since_dt.timestamp() * 1000)
        assert captured_params[0]["since"] == expected_ms

    async def test_lichess_without_since_no_param(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that without since parameter, no since is passed to API."""
        captured_params: list[dict] = []

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            captured_params.append(kwargs.get("params", {}))
            return create_mock_response(text="")

        client = MagicMock()
        client.get = mock_get
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        await lichess.fetch("testuser")

        assert len(captured_params) > 0
        assert "since" not in captured_params[0]

    async def test_chesscom_since_filters_archives(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that Chess.com filters out archives before since date."""
        from datetime import UTC, datetime

        archives_response = {
            "archives": [
                "https://api.chess.com/pub/player/test/games/2023/11",
                "https://api.chess.com/pub/player/test/games/2023/12",
                "https://api.chess.com/pub/player/test/games/2024/01",
                "https://api.chess.com/pub/player/test/games/2024/02",
            ]
        }
        games_response = {"games": [{"pgn": SAMPLE_PGN_1, "end_time": 1706000000}]}
        fetched_urls: list[str] = []

        def handler(url: str) -> MagicMock:
            fetched_urls.append(url)
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        # Since January 2024 - should skip 2023 archives
        since_dt = datetime(2024, 1, 1, tzinfo=UTC)
        await chesscom.fetch("testuser", since=since_dt)

        # Should only fetch 2024/01 and 2024/02, not 2023 archives
        archive_fetches = [u for u in fetched_urls if "archives" not in u]
        assert len(archive_fetches) == 2
        assert all("2024" in u for u in archive_fetches)
        assert not any("2023" in u for u in archive_fetches)

    async def test_chesscom_since_filters_games_within_archive(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that Chess.com filters out games before since timestamp."""
        from datetime import UTC, datetime

        archives_response = {
            "archives": ["https://api.chess.com/pub/player/test/games/2024/01"]
        }
        # Games with different timestamps
        games_response = {
            "games": [
                {
                    "pgn": SAMPLE_PGN_3,
                    "end_time": 1704100000,
                },  # Early Jan - before since
                {"pgn": SAMPLE_PGN_2, "end_time": 1705000000},  # Mid Jan - before since
                {"pgn": SAMPLE_PGN_1, "end_time": 1706000000},  # Late Jan - after since
            ]
        }

        def handler(url: str) -> MagicMock:
            if "archives" in url:
                return create_mock_response(json_data=archives_response)
            return create_mock_response(json_data=games_response)

        mock_client = create_mock_client(handler)
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

        # Since timestamp between game 2 and game 3
        since_dt = datetime(2024, 1, 20, tzinfo=UTC)  # 1705708800
        games, _ = await chesscom.fetch("testuser", since=since_dt)

        # Should only get the one game after since
        assert len(games) == 1


class TestRetryBehavior:
    async def test_retries_on_500_error(self, monkeypatch: pytest.MonkeyPatch):
        call_count = 0

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return create_mock_response(status_code=500, text="Server Error")

        client = MagicMock()
        client.get = mock_get

        with pytest.raises(MaxAttemptsExceeded):
            await fetch_with_retry(client, "https://example.com")

        assert call_count == 4  # 1 initial + 3 retries

    async def test_retries_on_429_error(self, monkeypatch: pytest.MonkeyPatch):
        call_count = 0

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return create_mock_response(status_code=429, text="Rate Limited")

        client = MagicMock()
        client.get = mock_get

        with pytest.raises(MaxAttemptsExceeded):
            await fetch_with_retry(client, "https://example.com")

        assert call_count == 4  # 1 initial + 3 retries

    async def test_no_retry_on_404_error(self, monkeypatch: pytest.MonkeyPatch):
        call_count = 0

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return create_mock_response(status_code=404, text="Not Found")

        client = MagicMock()
        client.get = mock_get

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(client, "https://example.com")

        assert call_count == 1  # No retries for 4xx

    async def test_succeeds_after_transient_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        call_count = 0

        async def mock_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return create_mock_response(status_code=500, text="Server Error")
            return create_mock_response(status_code=200, text="OK")

        client = MagicMock()
        client.get = mock_get

        response = await fetch_with_retry(client, "https://example.com")

        assert response.status_code == 200
        assert call_count == 3  # Failed twice, succeeded on third
