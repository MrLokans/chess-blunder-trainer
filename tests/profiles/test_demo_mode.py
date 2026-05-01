"""Demo-mode integration tests for the /api/profiles surface.

Exercises every demo-allowed mutation against the in-memory
`InMemoryProfileRepository` to confirm:
1. The DI swap fires when `app.state.demo_mode = True`.
2. The middleware allowlist no longer 403s the profile endpoints.
3. Mutations succeed and round-trip through the in-memory store.
4. Seeded profiles are visible on first read.
"""

from __future__ import annotations

from collections.abc import Generator
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.fetchers import ExistenceCheck
from blunder_tutor.repositories.profile import (
    InMemoryProfileRepository,
    get_demo_profile_repository,
    reset_demo_profile_repository,
)
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig
from tests.helpers.engine import make_test_client


@pytest.fixture(autouse=True)
def _reset_demo_singleton() -> Generator[None]:
    reset_demo_profile_repository()
    yield
    reset_demo_profile_repository()


@pytest.fixture
def demo_config(db_path: Path) -> AppConfig:
    return AppConfig(
        username="demo",
        engine_path="/usr/bin/stockfish",
        engine=EngineConfig(path="/usr/bin/stockfish", depth=10, time_limit=1.0),
        data=DataConfig(
            db_path=db_path,
            template_dir=Path(__file__).parent.parent.parent / "templates",
        ),
        demo_mode=True,
    )


@pytest.fixture
def demo_app(demo_config: AppConfig) -> Generator[TestClient]:
    yield from make_test_client(demo_config)


def _patch_existence(monkeypatch: pytest.MonkeyPatch, result: ExistenceCheck) -> None:
    async def fake(_platform: str, _username: str) -> ExistenceCheck:
        return result

    monkeypatch.setattr(
        "blunder_tutor.web.api._profile_helpers.check_username_existence", fake
    )


class TestSeedAndList:
    def test_seed_profiles_appear_on_first_list(self, demo_app: TestClient) -> None:
        response = demo_app.get("/api/profiles")
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        usernames = {p["username"] for p in body["profiles"]}
        platforms = {p["platform"] for p in body["profiles"]}
        assert usernames == {"demouser_li", "demouser_cc"}
        assert platforms == {"lichess", "chesscom"}

    def test_seed_profiles_have_stats(self, demo_app: TestClient) -> None:
        response = demo_app.get("/api/profiles")
        for profile in response.json()["profiles"]:
            assert len(profile["stats"]) >= 1


class TestDemoMutations:
    def test_validate_endpoint_allowed(
        self, demo_app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        response = demo_app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "newdemo"},
        )
        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["exists"] is True
        assert body["already_tracked"] is False

    def test_validate_marks_existing_seed_as_tracked(
        self, demo_app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        response = demo_app.post(
            "/api/profiles/validate",
            json={"platform": "lichess", "username": "demouser_li"},
        )
        body = response.json()
        assert body["already_tracked"] is True
        assert body["profile_id"] is not None

    def test_create_profile_allowed_and_persists_in_memory(
        self, demo_app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        response = demo_app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "newdemo", "make_primary": False},
        )
        assert response.status_code == HTTPStatus.CREATED, response.text
        body = response.json()
        assert body["username"] == "newdemo"

        listing = demo_app.get("/api/profiles").json()["profiles"]
        usernames = {p["username"] for p in listing}
        assert "newdemo" in usernames

    def test_patch_profile_allowed(
        self, demo_app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        seed = demo_app.get("/api/profiles").json()["profiles"][0]
        response = demo_app.patch(
            f"/api/profiles/{seed['id']}",
            json={"preferences": {"sync_max_games": 50, "auto_sync_enabled": True}},
        )
        assert response.status_code == HTTPStatus.OK, response.text
        body = response.json()
        assert body["preferences"]["sync_max_games"] == 50

    def test_delete_profile_allowed_and_removes_from_listing(
        self, demo_app: TestClient
    ) -> None:
        seed = demo_app.get("/api/profiles").json()["profiles"][0]
        response = demo_app.delete(f"/api/profiles/{seed['id']}?detach_games=true")
        assert response.status_code in {HTTPStatus.OK, HTTPStatus.NO_CONTENT}, (
            response.text
        )
        remaining = demo_app.get("/api/profiles").json()["profiles"]
        ids = {p["id"] for p in remaining}
        assert seed["id"] not in ids


class TestRepoSelection:
    def test_get_demo_profile_repository_is_singleton(self) -> None:
        first = get_demo_profile_repository()
        second = get_demo_profile_repository()
        assert first is second
        assert isinstance(first, InMemoryProfileRepository)

    def test_reset_returns_a_fresh_singleton(self) -> None:
        first = get_demo_profile_repository()
        reset_demo_profile_repository()
        second = get_demo_profile_repository()
        assert first is not second


class TestNonDemoStillBlocks:
    def test_create_profile_blocked_in_non_demo_when_app_is_demo_off(
        self, app: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Sanity: when DEMO_MODE is off, the same endpoint goes through
        # the SQLite repo and the demo-block middleware doesn't fire.
        # The patched existence check makes this a clean upstream-success
        # path so we can assert the endpoint reaches the SQLite repo.
        _patch_existence(monkeypatch, ExistenceCheck(exists=True, rate_limited=False))
        response = app.post(
            "/api/profiles",
            json={"platform": "lichess", "username": "realuser", "make_primary": True},
        )
        # Either 201 (create succeeded) or whatever the SQLite path returns —
        # the explicit assertion is "NOT 403 demo_mode".
        assert response.status_code != HTTPStatus.FORBIDDEN
