from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from blunder_tutor.auth import AuthService, Username
from blunder_tutor.web.auth_hooks import resolve_user_db_path


@pytest.fixture
def service(service_factory) -> AuthService:
    return service_factory(
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )


class TestPerUserDbInit:
    async def test_signup_creates_per_user_db_file(
        self, service: AuthService, tmp_path: Path
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        path = resolve_user_db_path(tmp_path / "users", user.id)
        assert path.exists()
        assert path.name == "main.sqlite3"

    async def test_signup_runs_migrations_on_per_user_db(
        self, service: AuthService, tmp_path: Path
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        path = resolve_user_db_path(tmp_path / "users", user.id)
        with sqlite3.connect(path) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND "
                "name='game_index_cache'"
            )
            assert cur.fetchone() is not None

    async def test_two_users_get_isolated_dbs(
        self, service: AuthService, tmp_path: Path
    ):
        a = await service.register(username=Username("alice"), password="password123")
        b = await service.register(username=Username("bob"), password="password123")
        users_dir = tmp_path / "users"
        path_a = resolve_user_db_path(users_dir, a.id)
        path_b = resolve_user_db_path(users_dir, b.id)
        assert path_a != path_b
        assert path_a.exists() and path_b.exists()
