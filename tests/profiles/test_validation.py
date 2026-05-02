from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.fetchers import ExistenceCheck
from blunder_tutor.fetchers.resilience import RetryableHTTPError
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig
from tests.helpers.engine import make_test_client


@pytest.fixture
def demo_config(db_path: Path) -> AppConfig:
    return AppConfig(
        username="testuser",
        engine_path="/usr/bin/stockfish",
        engine=EngineConfig(path="/usr/bin/stockfish", depth=10, time_limit=1.0),
        data=DataConfig(
            db_path=db_path,
            template_dir=Path(__file__).parent.parent.parent / "templates",
        ),
        demo_mode=True,
    )


@pytest.fixture
def demo_app(demo_config: AppConfig):
    yield from make_test_client(demo_config)


def _patch_existence(
    monkeypatch: pytest.MonkeyPatch, result: ExistenceCheck
) -> list[tuple[str, str]]:
    captured: list[tuple[str, str]] = []

    async def fake(platform: str, username: str) -> ExistenceCheck:
        captured.append((platform, username))
        return result

    # Single source of truth: all three handlers (validate, create, update)
    # reach the upstream existence check through `_profile_helpers`.
    monkeypatch.setattr(
        "blunder_tutor.web.api._profile_helpers.check_username_existence", fake
    )
    return captured


class TestValidateEndpoint:
    def test_exists_true_no_profile_yet(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))

        response = app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body == {
            "exists": True,
            "already_tracked": False,
            "profile_id": None,
            "rate_limited": False,
        }

    async def test_exists_true_already_tracked(
        self,
        app: TestClient,
        db_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")

        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))

        response = app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "ALICE"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body == {
            "exists": True,
            "already_tracked": True,
            "profile_id": profile.id,
            "rate_limited": False,
        }

    def test_exists_false_for_404(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=False, rate_limited=False))

        response = app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "nobody"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["exists"] is False
        assert body["already_tracked"] is False
        assert body["rate_limited"] is False

    def test_rate_limited_returns_signal(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=False, rate_limited=True))

        response = app.post(
            "/api/profiles/validate",
            json={"platform": "chesscom", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["rate_limited"] is True
        assert body["exists"] is False

    def test_invalid_platform_returns_422(self, app: TestClient) -> None:
        response = app.post(
            "/api/profiles/validate",
            json={"platform": "fide", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_empty_username_returns_422(self, app: TestClient) -> None:
        response = app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": ""},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_upstream_5xx_returns_502(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        response_500 = MagicMock()
        response_500.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

        async def fake(_platform: str, _username: str) -> ExistenceCheck:
            raise RetryableHTTPError(response_500)

        monkeypatch.setattr(
            "blunder_tutor.web.api._profile_helpers.check_username_existence", fake
        )

        response = app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "alice"},
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY


class TestValidateEndpointDemoMode:
    def test_allowed_in_demo_mode(
        self, demo_app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))

        response = demo_app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "alice"},
        )
        # Not 403 — endpoint is read-only against external APIs.
        assert response.status_code == HTTPStatus.OK
        assert response.json()["exists"] is True


class TestExistenceCheckCallSite:
    def test_passes_platform_and_normalized_username(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = _patch_existence(
            monkeypatch, ExistenceCheck(exists=True, rate_limited=False)
        )

        app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "  Alice  "},
        )

        # Whitespace stripped; original casing preserved (the existence check
        # itself decides whether to lowercase per platform).
        assert captured == [("lichess", "Alice")]
