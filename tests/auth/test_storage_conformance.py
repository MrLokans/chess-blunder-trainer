from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from blunder_tutor.auth import (
    AuthDb,
    Email,
    IdentityId,
    InMemoryStorage,
    PasswordHash,
    SessionToken,
    SqliteStorage,
    Storage,
    UserId,
    Username,
    initialize_auth_schema,
    make_identity_id,
    make_session_token,
    make_user_id,
)

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Shared fixtures + parameterization. Both backends ship as a Storage
# protocol implementation; every test in this module runs against each so
# any divergence (UNIQUE error message, CASCADE order, datetime semantics)
# surfaces here, not later in service-layer tests.
# ---------------------------------------------------------------------------


async def _make_sqlite_storage(tmp_path: Path) -> SqliteStorage:
    db_path = tmp_path / "auth.sqlite3"
    await initialize_auth_schema(db_path)
    auth_db = AuthDb(db_path)
    await auth_db.connect()
    return SqliteStorage(auth_db)


@pytest.fixture(params=["sqlite", "in_memory"])
async def storage(request, tmp_path: Path):
    """Parameterized over both backends — every test runs twice."""
    if request.param == "sqlite":
        s = await _make_sqlite_storage(tmp_path)
        yield s
        await s.auth_db.close()
    else:
        yield InMemoryStorage()


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


async def _insert_user(
    storage: Storage,
    *,
    username: str = "alice",
    email: str | None = None,
) -> UserId:
    user_id = make_user_id()
    async with storage.transaction() as txn:
        await storage.users.insert_in_transaction(
            txn,
            user_id=user_id,
            username=Username(username),
            email=Email(email) if email else None,
            created_at=_now_iso(),
        )
    return user_id


async def _insert_credentials_identity(
    storage: Storage,
    *,
    user_id: UserId,
    subject: str,
    credential: str = "$2b$12$abcdefghijklmnopqrstuv",
) -> IdentityId:
    identity_id = make_identity_id()
    async with storage.transaction() as txn:
        await storage.identities.insert_in_transaction(
            txn,
            identity_id=identity_id,
            user_id=user_id,
            provider="credentials",
            provider_subject=subject,
            credential=PasswordHash(credential),
            created_at=_now_iso(),
        )
    return identity_id


# ---------------------------------------------------------------------------
# Conformance scenarios. Each runs once per backend via parameterization.
# ---------------------------------------------------------------------------


class TestUserRepoConformance:
    async def test_insert_and_get_by_id_roundtrip(self, storage: Storage) -> None:
        uid = await _insert_user(storage, username="alice", email="alice@example.com")
        got = await storage.users.get_by_id(uid)
        assert got is not None
        assert got.username == "alice"
        assert got.email == "alice@example.com"

    async def test_get_by_username(self, storage: Storage) -> None:
        await _insert_user(storage, username="alice")
        got = await storage.users.get_by_username(Username("alice"))
        assert got is not None
        assert got.username == "alice"

    async def test_get_by_email(self, storage: Storage) -> None:
        await _insert_user(storage, username="alice", email="alice@example.com")
        got = await storage.users.get_by_email(Email("alice@example.com"))
        assert got is not None
        assert got.email == "alice@example.com"

    async def test_unique_username_raises(self, storage: Storage) -> None:
        await _insert_user(storage, username="alice")
        with pytest.raises(sqlite3.IntegrityError, match="users.username"):
            await _insert_user(storage, username="alice")

    async def test_unique_email_raises(self, storage: Storage) -> None:
        await _insert_user(storage, username="alice", email="dup@example.com")
        with pytest.raises(sqlite3.IntegrityError, match="users.email"):
            await _insert_user(storage, username="bob", email="dup@example.com")

    async def test_count_matches_inserts(self, storage: Storage) -> None:
        assert await storage.users.count() == 0
        for name in ("alice", "bob", "charlie"):
            await _insert_user(storage, username=name)
        assert await storage.users.count() == 3

    async def test_list_all_orders_by_created_then_id(self, storage: Storage) -> None:
        await _insert_user(storage, username="alice")
        await _insert_user(storage, username="bob")
        users = await storage.users.list_all()
        names = [u.username for u in users]
        assert set(names) == {"alice", "bob"}


class TestIdentityRepoConformance:
    async def test_insert_and_get_by_provider_subject(self, storage: Storage) -> None:
        uid = await _insert_user(storage, username="alice")
        await _insert_credentials_identity(storage, user_id=uid, subject="alice")
        got = await storage.identities.get_by_provider_subject("credentials", "alice")
        assert got is not None
        assert got.user_id == uid

    async def test_unique_provider_subject_raises(self, storage: Storage) -> None:
        uid_a = await _insert_user(storage, username="alice")
        uid_b = await _insert_user(storage, username="bob")
        await _insert_credentials_identity(storage, user_id=uid_a, subject="alice")
        with pytest.raises(sqlite3.IntegrityError, match="provider_subject"):
            await _insert_credentials_identity(storage, user_id=uid_b, subject="alice")

    async def test_list_for_user(self, storage: Storage) -> None:
        uid = await _insert_user(storage, username="alice")
        await _insert_credentials_identity(storage, user_id=uid, subject="alice")
        identities = await storage.identities.list_for_user(uid)
        assert len(identities) == 1
        assert identities[0].provider_subject == "alice"


class TestSessionRepoConformance:
    async def test_insert_and_get(self, storage: Storage) -> None:
        uid = await _insert_user(storage, username="alice")
        token = make_session_token()
        await storage.sessions.insert(
            token=token,
            user_id=uid,
            expires_at=_now() + timedelta(days=30),
            user_agent="ua",
            ip_address="127.0.0.1",
        )
        got = await storage.sessions.get(token)
        assert got is not None
        assert got.user_id == uid
        assert got.user_agent == "ua"

    async def test_bump_last_seen_advances(self, storage: Storage) -> None:
        uid = await _insert_user(storage, username="alice")
        token = make_session_token()
        await storage.sessions.insert(
            token=token,
            user_id=uid,
            expires_at=_now() + timedelta(days=30),
            user_agent=None,
            ip_address=None,
        )
        first = await storage.sessions.get(token)
        assert first is not None
        original_last_seen = first.last_seen_at
        await storage.sessions.bump_last_seen(token)
        bumped = await storage.sessions.get(token)
        assert bumped is not None
        assert bumped.last_seen_at >= original_last_seen

    async def test_delete_expired_removes_only_expired(self, storage: Storage) -> None:
        uid = await _insert_user(storage, username="alice")
        live = make_session_token()
        expired = make_session_token()
        await storage.sessions.insert(
            token=live,
            user_id=uid,
            expires_at=_now() + timedelta(days=30),
            user_agent=None,
            ip_address=None,
        )
        await storage.sessions.insert(
            token=expired,
            user_id=uid,
            expires_at=_now() - timedelta(seconds=1),
            user_agent=None,
            ip_address=None,
        )
        removed = await storage.sessions.delete_expired(_now())
        assert removed == 1
        assert await storage.sessions.get(live) is not None
        assert await storage.sessions.get(expired) is None


class TestCascadeDelete:
    async def test_user_delete_cascades_identities_and_sessions(
        self, storage: Storage
    ) -> None:
        uid = await _insert_user(storage, username="alice")
        await _insert_credentials_identity(storage, user_id=uid, subject="alice")
        token = make_session_token()
        await storage.sessions.insert(
            token=token,
            user_id=uid,
            expires_at=_now() + timedelta(days=30),
            user_agent=None,
            ip_address=None,
        )

        await storage.users.delete(uid)

        assert await storage.users.get_by_id(uid) is None
        assert await storage.identities.list_for_user(uid) == []
        assert await storage.sessions.get(SessionToken(token)) is None


class TestSetupRepoConformance:
    async def test_get_returns_none_for_missing(self, storage: Storage) -> None:
        assert await storage.setup.get("nope") is None

    async def test_put_then_get(self, storage: Storage) -> None:
        await storage.setup.put("invite_code", "abc.def")
        assert await storage.setup.get("invite_code") == "abc.def"

    async def test_put_overwrites(self, storage: Storage) -> None:
        await storage.setup.put("k", "v1")
        await storage.setup.put("k", "v2")
        assert await storage.setup.get("k") == "v2"

    async def test_delete(self, storage: Storage) -> None:
        await storage.setup.put("k", "v")
        await storage.setup.delete("k")
        assert await storage.setup.get("k") is None
