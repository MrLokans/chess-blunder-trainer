from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.repository import SessionRepository
from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import SessionToken, Username


@pytest.fixture
async def service(auth_db: AuthDb, tmp_path) -> AuthService:
    users_dir = tmp_path / "users"
    users_dir.mkdir()
    return AuthService(
        auth_db=auth_db,
        users_dir=users_dir,
        session_max_age=timedelta(seconds=60),
        session_idle=timedelta(seconds=30),
    )


async def _force_column(
    auth_db: AuthDb, token: SessionToken, column: str, value: datetime
) -> None:
    conn = await auth_db.conn()
    await conn.execute(
        f"UPDATE sessions SET {column} = ? WHERE token = ?",
        (value.isoformat(), token),
    )
    await conn.commit()


class TestSessionResolution:
    async def test_fresh_session_resolves(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent="ua", ip="127.0.0.1"
        )
        ctx = await service.resolve_session(session.token, "127.0.0.1")
        assert ctx is not None
        assert ctx.user_id == user.id
        assert ctx.username == user.username
        assert ctx.session_token == session.token

    async def test_invalid_token_returns_none(self, service: AuthService):
        assert await service.resolve_session("not-a-real-token", None) is None

    async def test_empty_token_returns_none(self, service: AuthService):
        assert await service.resolve_session("", None) is None

    async def test_absolute_expiry(self, service: AuthService, auth_db: AuthDb):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        await _force_column(
            auth_db,
            session.token,
            "expires_at",
            datetime.now(UTC) - timedelta(seconds=1),
        )

        assert await service.resolve_session(session.token, None) is None

        repo = SessionRepository(db=auth_db)
        assert await repo.get(session.token) is None

    async def test_idle_expiry(self, service: AuthService, auth_db: AuthDb):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        await _force_column(
            auth_db,
            session.token,
            "last_seen_at",
            datetime.now(UTC) - timedelta(minutes=5),
        )

        assert await service.resolve_session(session.token, None) is None

        repo = SessionRepository(db=auth_db)
        assert await repo.get(session.token) is None

    async def test_resolve_bumps_last_seen(self, service: AuthService, auth_db: AuthDb):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        await _force_column(
            auth_db,
            session.token,
            "last_seen_at",
            datetime.now(UTC) - timedelta(seconds=15),
        )

        repo = SessionRepository(db=auth_db)
        before = (await repo.get(session.token)).last_seen_at

        ctx = await service.resolve_session(session.token, None)
        assert ctx is not None

        after = (await repo.get(session.token)).last_seen_at
        assert after > before


class TestRevocation:
    async def test_revoke_single(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        await service.revoke_session(session.token)
        assert await service.resolve_session(session.token, None) is None

    async def test_revoke_all(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        tokens = []
        for _ in range(3):
            s = await service.create_session(user_id=user.id, user_agent=None, ip=None)
            tokens.append(s.token)
        await service.revoke_all_sessions(user.id)
        for tok in tokens:
            assert await service.resolve_session(tok, None) is None

    async def test_revoke_all_spares_other_users(self, service: AuthService):
        alice = await service.register(
            username=Username("alice"), password="password123"
        )
        bob = await service.register(username=Username("bob"), password="password123")
        bob_session = await service.create_session(
            user_id=bob.id, user_agent=None, ip=None
        )

        await service.revoke_all_sessions(alice.id)

        assert await service.resolve_session(bob_session.token, None) is not None


class TestSessionIsolation:
    async def test_orphaned_session_row_is_cleaned_up(
        self, service: AuthService, auth_db: AuthDb
    ):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent=None, ip=None
        )
        # Manually break referential integrity via the shared connection.
        conn = await auth_db.conn()
        await conn.execute("PRAGMA foreign_keys = OFF")
        await conn.execute("DELETE FROM users WHERE id = ?", (user.id,))
        await conn.commit()
        await conn.execute("PRAGMA foreign_keys = ON")

        assert await service.resolve_session(session.token, None) is None
