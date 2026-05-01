from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from blunder_tutor.fetchers.chesscom import validate_username as chesscom_validate
from blunder_tutor.fetchers.lichess import validate_username as lichess_validate
from blunder_tutor.fetchers.validation import validate_username


def _mock_response(status_code: int) -> httpx.Response:
    return httpx.Response(
        status_code=status_code, request=httpx.Request("GET", "http://test")
    )


@pytest.mark.asyncio
async def test_lichess_validate_existing_user():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(200))

    with patch(
        "blunder_tutor.fetchers.lichess.httpx.AsyncClient", return_value=mock_client
    ):
        assert await lichess_validate("DrNykterstein") is True


@pytest.mark.asyncio
async def test_lichess_validate_nonexistent_user():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(404))

    with patch(
        "blunder_tutor.fetchers.lichess.httpx.AsyncClient", return_value=mock_client
    ):
        assert await lichess_validate("thisuserdoesnotexist999") is False


@pytest.mark.asyncio
async def test_chesscom_validate_existing_user():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(200))

    with patch(
        "blunder_tutor.fetchers.chesscom.httpx.AsyncClient", return_value=mock_client
    ):
        assert await chesscom_validate("MagnusCarlsen") is True


@pytest.mark.asyncio
async def test_chesscom_validate_nonexistent_user():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_mock_response(404))

    with patch(
        "blunder_tutor.fetchers.chesscom.httpx.AsyncClient", return_value=mock_client
    ):
        assert await chesscom_validate("thisuserdoesnotexist999") is False


@pytest.mark.asyncio
async def test_lichess_validate_handles_network_error():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with patch(
        "blunder_tutor.fetchers.lichess.httpx.AsyncClient", return_value=mock_client
    ):
        assert await lichess_validate("anyuser") is False


@pytest.mark.asyncio
async def test_validate_username_dispatcher():
    with patch.dict(
        "blunder_tutor.fetchers.validation.VALIDATORS",
        {"lichess": AsyncMock(return_value=True)},
    ):
        assert await validate_username("lichess", "test") is True

    with patch.dict(
        "blunder_tutor.fetchers.validation.VALIDATORS",
        {"chesscom": AsyncMock(return_value=False)},
    ):
        assert await validate_username("chesscom", "test") is False


@pytest.mark.asyncio
async def test_validate_username_unknown_platform():
    assert await validate_username("unknown_platform", "test") is False
