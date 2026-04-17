from __future__ import annotations

from datetime import UTC, datetime, timedelta

import aiosqlite
import pytest

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.repository import (
    IdentityRepository,
    SessionRepository,
    SetupRepository,
    UserRepository,
)
from blunder_tutor.auth.types import (
    Email,
    PasswordHash,
    Username,
    make_identity_id,
    make_session_token,
    make_user_id,
)


class TestUserRepository:
    async def test_insert_and_fetch_by_id(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        uid = make_user_id()
        await repo.insert(
            user_id=uid,
            username=Username("alice"),
            email=Email("alice@example.com"),
        )
        user = await repo.get_by_id(uid)
        assert user is not None
        assert user.id == uid
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.created_at.tzinfo is not None

    async def test_fetch_by_username(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        uid = make_user_id()
        await repo.insert(user_id=uid, username=Username("bob"), email=None)
        user = await repo.get_by_username(Username("bob"))
        assert user is not None
        assert user.id == uid

    async def test_fetch_by_email(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        uid = make_user_id()
        await repo.insert(
            user_id=uid,
            username=Username("eve"),
            email=Email("eve@example.com"),
        )
        user = await repo.get_by_email(Email("eve@example.com"))
        assert user is not None
        assert user.id == uid

    async def test_missing_lookups_return_none(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        assert await repo.get_by_id(make_user_id()) is None
        assert await repo.get_by_username(Username("ghost")) is None
        assert await repo.get_by_email(Email("ghost@example.com")) is None

    async def test_unique_username(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        await repo.insert(
            user_id=make_user_id(), username=Username("alice"), email=None
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await repo.insert(
                user_id=make_user_id(),
                username=Username("alice"),
                email=None,
            )

    async def test_unique_email(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        await repo.insert(
            user_id=make_user_id(),
            username=Username("alice"),
            email=Email("a@b.com"),
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await repo.insert(
                user_id=make_user_id(),
                username=Username("bob"),
                email=Email("a@b.com"),
            )

    async def test_count(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        assert await repo.count() == 0
        await repo.insert(
            user_id=make_user_id(), username=Username("alice"), email=None
        )
        await repo.insert(user_id=make_user_id(), username=Username("bob"), email=None)
        assert await repo.count() == 2

    async def test_list_all_is_stable(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        for name in ("alice", "bob", "carol"):
            await repo.insert(
                user_id=make_user_id(), username=Username(name), email=None
            )
        first = [u.username for u in await repo.list_all()]
        second = [u.username for u in await repo.list_all()]
        assert set(first) == {"alice", "bob", "carol"}
        assert first == second

    async def test_delete_cascades_identities_and_sessions(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        sessions = SessionRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        await identities.insert(
            identity_id=make_identity_id(),
            user_id=uid,
            provider="credentials",
            provider_subject="alice",
            credential=PasswordHash("$2b$12$abcdef"),
        )
        await sessions.insert(
            token=make_session_token(),
            user_id=uid,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            user_agent="ua",
            ip_address="127.0.0.1",
        )

        await users.delete(uid)

        assert await identities.list_for_user(uid) == []
        assert await sessions.list_for_user(uid) == []
        assert await users.get_by_id(uid) is None


class TestIdentityRepository:
    async def test_lookup_by_provider_subject(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        await identities.insert(
            identity_id=make_identity_id(),
            user_id=uid,
            provider="credentials",
            provider_subject="alice",
            credential=PasswordHash("$2b$12$abcdef"),
        )
        ident = await identities.get_by_provider_subject("credentials", "alice")
        assert ident is not None
        assert ident.user_id == uid
        assert ident.provider == "credentials"
        assert ident.credential == "$2b$12$abcdef"

    async def test_unique_provider_subject(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        uid_a = make_user_id()
        uid_b = make_user_id()
        await users.insert(user_id=uid_a, username=Username("alice"), email=None)
        await users.insert(user_id=uid_b, username=Username("bob"), email=None)
        await identities.insert(
            identity_id=make_identity_id(),
            user_id=uid_a,
            provider="credentials",
            provider_subject="shared",
            credential=None,
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await identities.insert(
                identity_id=make_identity_id(),
                user_id=uid_b,
                provider="credentials",
                provider_subject="shared",
                credential=None,
            )

    async def test_update_credential(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        ident_id = make_identity_id()
        await identities.insert(
            identity_id=ident_id,
            user_id=uid,
            provider="credentials",
            provider_subject="alice",
            credential=PasswordHash("$2b$12$old"),
        )
        await identities.update_credential(ident_id, PasswordHash("$2b$12$new"))
        ident = await identities.get_by_provider_subject("credentials", "alice")
        assert ident is not None
        assert ident.credential == "$2b$12$new"


class TestSessionRepository:
    async def test_roundtrip(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        sessions = SessionRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        token = make_session_token()
        expires = datetime.now(UTC) + timedelta(days=1)
        await sessions.insert(
            token=token,
            user_id=uid,
            expires_at=expires,
            user_agent="Mozilla/5.0",
            ip_address="127.0.0.1",
        )
        s = await sessions.get(token)
        assert s is not None
        assert s.user_id == uid
        assert s.token == token
        assert s.user_agent == "Mozilla/5.0"
        assert s.ip_address == "127.0.0.1"
        assert s.expires_at.tzinfo is not None

    async def test_bump_last_seen_monotonic(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        sessions = SessionRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        token = make_session_token()
        now = datetime.now(UTC)
        await sessions.insert(
            token=token,
            user_id=uid,
            expires_at=now + timedelta(days=1),
            user_agent=None,
            ip_address=None,
        )
        # Force last_seen back via direct SQL to make the bump observable.
        conn = await auth_db.conn()
        await conn.execute(
            "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
            ((now - timedelta(hours=1)).isoformat(), token),
        )
        await conn.commit()

        before = (await sessions.get(token)).last_seen_at
        await sessions.bump_last_seen(token)
        after = (await sessions.get(token)).last_seen_at
        assert after > before

    async def test_delete_single(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        sessions = SessionRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        token = make_session_token()
        await sessions.insert(
            token=token,
            user_id=uid,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            user_agent=None,
            ip_address=None,
        )
        await sessions.delete(token)
        assert await sessions.get(token) is None

    async def test_delete_all_for_user(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        sessions = SessionRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        for _ in range(3):
            await sessions.insert(
                token=make_session_token(),
                user_id=uid,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                user_agent=None,
                ip_address=None,
            )
        assert len(await sessions.list_for_user(uid)) == 3
        await sessions.delete_all_for_user(uid)
        assert await sessions.list_for_user(uid) == []

    async def test_delete_expired(self, auth_db: AuthDb):
        users = UserRepository(db=auth_db)
        sessions = SessionRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        now = datetime.now(UTC)
        fresh = make_session_token()
        stale = make_session_token()
        await sessions.insert(
            token=fresh,
            user_id=uid,
            expires_at=now + timedelta(days=1),
            user_agent=None,
            ip_address=None,
        )
        await sessions.insert(
            token=stale,
            user_id=uid,
            expires_at=now - timedelta(days=1),
            user_agent=None,
            ip_address=None,
        )
        removed = await sessions.delete_expired(as_of=now)
        assert removed == 1
        assert await sessions.get(fresh) is not None
        assert await sessions.get(stale) is None


class TestSetupRepository:
    async def test_put_get_delete(self, auth_db: AuthDb):
        repo = SetupRepository(db=auth_db)
        assert await repo.get("invite_code") is None
        await repo.put("invite_code", "abc.def")
        assert await repo.get("invite_code") == "abc.def"
        await repo.delete("invite_code")
        assert await repo.get("invite_code") is None

    async def test_put_overwrites(self, auth_db: AuthDb):
        repo = SetupRepository(db=auth_db)
        await repo.put("k", "v1")
        await repo.put("k", "v2")
        assert await repo.get("k") == "v2"


class TestBrandedTypeRewrap:
    async def test_user_returns_branded_types(self, auth_db: AuthDb):
        repo = UserRepository(db=auth_db)
        uid = make_user_id()
        await repo.insert(
            user_id=uid,
            username=Username("alice"),
            email=Email("alice@example.com"),
        )
        user = await repo.get_by_id(uid)
        assert user is not None
        assert isinstance(user.id, str)
        assert isinstance(user.username, str)
        assert isinstance(user.email, str)
        assert user.id == uid


class TestConnectionReopen:
    async def test_pragma_foreign_keys_reapplied_after_reconnect(self, auth_db: AuthDb):
        """If the AuthDb connection is closed and reopened (e.g. process
        recycling), `PRAGMA foreign_keys` must be re-applied — otherwise
        ON DELETE CASCADE silently no-ops."""
        users = UserRepository(db=auth_db)
        identities = IdentityRepository(db=auth_db)
        uid = make_user_id()
        await users.insert(user_id=uid, username=Username("alice"), email=None)
        await identities.insert(
            identity_id=make_identity_id(),
            user_id=uid,
            provider="credentials",
            provider_subject="alice",
            credential=PasswordHash("$2b$12$abcdef"),
        )

        await auth_db.close()
        await auth_db.connect()

        await users.delete(uid)
        assert await identities.list_for_user(uid) == []
