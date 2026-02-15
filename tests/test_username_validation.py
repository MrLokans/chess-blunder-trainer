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


def test_validate_username_api_endpoint(app):
    with patch(
        "blunder_tutor.web.api.settings.validate_username",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = app.post(
            "/api/validate-username",
            json={"platform": "lichess", "username": "testuser"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["platform"] == "lichess"
        assert data["username"] == "testuser"


def test_validate_username_api_invalid_platform(app):
    resp = app.post(
        "/api/validate-username", json={"platform": "badplatform", "username": "test"}
    )
    assert resp.status_code == 400


def test_validate_username_api_empty_username(app):
    resp = app.post(
        "/api/validate-username", json={"platform": "lichess", "username": ""}
    )
    assert resp.status_code == 400


def test_setup_returns_import_job_ids(app):
    with patch(
        "blunder_tutor.web.api.settings.validate_username",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = app.post("/api/setup", json={"lichess": "testuser", "chesscom": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "import_job_ids" in data
        assert len(data["import_job_ids"]) == 1


def test_setup_returns_multiple_job_ids_for_both_platforms(app):
    with patch(
        "blunder_tutor.web.api.settings.validate_username",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = app.post("/api/setup", json={"lichess": "user1", "chesscom": "user2"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["import_job_ids"]) == 2


def test_setup_rejects_invalid_username(app):
    with patch(
        "blunder_tutor.web.api.settings.validate_username",
        new_callable=AsyncMock,
        return_value=False,
    ):
        resp = app.post("/api/setup", json={"lichess": "baduser", "chesscom": ""})
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()


def test_setup_rejects_one_invalid_of_two(app):
    async def mock_validate(platform: str, username: str) -> bool:
        return platform == "lichess"

    with patch(
        "blunder_tutor.web.api.settings.validate_username",
        side_effect=mock_validate,
    ):
        resp = app.post(
            "/api/setup", json={"lichess": "gooduser", "chesscom": "baduser"}
        )
        assert resp.status_code == 400
        assert "chess.com" in resp.json()["detail"].lower()
