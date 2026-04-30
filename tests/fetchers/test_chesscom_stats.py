from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from blunder_tutor.fetchers import RateLimitError, chesscom
from blunder_tutor.fetchers.resilience import RetryableHTTPError

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def chesscom_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "chesscom_player_stats.json").read_text())


def _patch_fetch_with_retry(
    monkeypatch: pytest.MonkeyPatch, behavior: Any
) -> list[str]:
    captured_urls: list[str] = []

    async def fake_fetch(_client: Any, url: str, **_kwargs: Any) -> Any:
        captured_urls.append(url)
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior

    monkeypatch.setattr("blunder_tutor.fetchers.chesscom.fetch_with_retry", fake_fetch)
    return captured_urls


class TestFetchUserStats:
    async def test_returns_canonical_snapshots(
        self,
        monkeypatch: pytest.MonkeyPatch,
        chesscom_payload: dict[str, Any],
    ) -> None:
        response = MagicMock()
        response.json = MagicMock(return_value=chesscom_payload)
        _patch_fetch_with_retry(monkeypatch, response)

        snapshots = await chesscom.fetch_user_stats("alice")
        modes = {snap.mode for snap in snapshots}
        assert modes == {"bullet", "blitz", "rapid", "correspondence"}

    async def test_lowercases_username_in_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        chesscom_payload: dict[str, Any],
    ) -> None:
        response = MagicMock()
        response.json = MagicMock(return_value=chesscom_payload)
        captured = _patch_fetch_with_retry(monkeypatch, response)

        await chesscom.fetch_user_stats("AliceCarlsen")

        assert captured == ["https://api.chess.com/pub/player/alicecarlsen/stats"]

    async def test_rate_limit_raises_rate_limit_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rate_limited = MagicMock()
        rate_limited.status_code = HTTPStatus.TOO_MANY_REQUESTS
        _patch_fetch_with_retry(monkeypatch, RetryableHTTPError(rate_limited))

        with pytest.raises(RateLimitError) as excinfo:
            await chesscom.fetch_user_stats("alice")
        assert excinfo.value.platform == "chesscom"

    async def test_404_propagates_as_http_status_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        request = MagicMock()
        response = MagicMock()
        response.status_code = HTTPStatus.NOT_FOUND
        _patch_fetch_with_retry(
            monkeypatch,
            httpx.HTTPStatusError("404", request=request, response=response),
        )

        with pytest.raises(httpx.HTTPStatusError):
            await chesscom.fetch_user_stats("ghost")

    async def test_empty_payload_returns_empty_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        response = MagicMock()
        response.json = MagicMock(return_value={})
        _patch_fetch_with_retry(monkeypatch, response)

        snapshots = await chesscom.fetch_user_stats("alice")
        assert not snapshots
