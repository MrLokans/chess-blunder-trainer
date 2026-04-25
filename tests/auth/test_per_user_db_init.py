from __future__ import annotations

import sqlite3
from datetime import timedelta

import pytest

from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import Username


@pytest.fixture
def service(service_factory) -> AuthService:
    return service_factory(
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )


class TestPerUserDbInit:
    async def test_signup_creates_per_user_db_file(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        path = service.db_path_for(user.id)
        assert path.exists()
        assert path.name == "main.sqlite3"

    async def test_signup_runs_migrations_on_per_user_db(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        path = service.db_path_for(user.id)
        with sqlite3.connect(path) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND "
                "name='game_index_cache'"
            )
            assert cur.fetchone() is not None

    async def test_two_users_get_isolated_dbs(self, service: AuthService):
        a = await service.register(username=Username("alice"), password="password123")
        b = await service.register(username=Username("bob"), password="password123")
        path_a = service.db_path_for(a.id)
        path_b = service.db_path_for(b.id)
        assert path_a != path_b
        assert path_a.exists() and path_b.exists()
