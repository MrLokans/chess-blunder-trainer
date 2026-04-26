from __future__ import annotations

from datetime import datetime

import aiosqlite

from blunder_tutor.auth.core._time import now_iso, parse_dt
from blunder_tutor.auth.core.types import (
    Email,
    Identity,
    IdentityId,
    PasswordHash,
    ProviderName,
    Session,
    SessionToken,
    User,
    UserId,
    Username,
)
from blunder_tutor.auth.storage_sqlite.db import AuthDb


class UserRepository:
    def __init__(self, db: AuthDb) -> None:
        self._db = db

    @staticmethod
    async def insert_in_transaction(
        conn,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
        created_at: str,
    ) -> None:
        """Single copy of the ``users`` INSERT. Callers own the transaction
        (and the write lock) so service-layer multi-table writes can share
        one ``BEGIN IMMEDIATE`` span with the ``identities`` INSERT."""
        await conn.execute(
            "INSERT INTO users (id, username, email, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, email, created_at),
        )

    async def insert(
        self,
        *,
        user_id: UserId,
        username: Username,
        email: Email | None,
    ) -> None:
        async with self._db.write() as conn:
            await self.insert_in_transaction(
                conn,
                user_id=user_id,
                username=username,
                email=email,
                created_at=now_iso(),
            )

    async def get_by_id(self, user_id: UserId) -> User | None:
        return await self._fetch_one("WHERE id = ?", (user_id,))

    async def get_by_username(self, username: Username) -> User | None:
        return await self._fetch_one("WHERE username = ?", (username,))

    async def get_by_email(self, email: Email) -> User | None:
        return await self._fetch_one("WHERE email = ?", (email,))

    async def count(self) -> int:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"
        ) as cur:
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def list_all(self) -> list[User]:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT id, username, email, created_at FROM users "
            "WHERE deleted_at IS NULL ORDER BY created_at, id"
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_user(r) for r in rows]

    async def delete(self, user_id: UserId) -> None:
        """Single-row hard delete. ON DELETE CASCADE on identities/sessions
        means a service-layer ``delete_account`` only needs to call this
        from inside ``AuthDb.transaction()``."""
        async with self._db.write() as conn:
            await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    async def _fetch_one(self, where: str, params: tuple) -> User | None:
        conn = await self._db.conn()
        async with conn.execute(
            f"SELECT id, username, email, created_at FROM users {where}",
            params,
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_user(row) if row else None

    @staticmethod
    def _row_to_user(row) -> User:
        uid, uname, email, created = row
        return User(
            id=UserId(uid),
            username=Username(uname),
            email=Email(email) if email else None,
            created_at=parse_dt(created),
        )


class IdentityRepository:
    def __init__(self, db: AuthDb) -> None:
        self._db = db

    @staticmethod
    async def insert_in_transaction(
        conn,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
        credential: PasswordHash | None,
        created_at: str,
    ) -> None:
        """Single copy of the ``identities`` INSERT. Paired with
        :meth:`UserRepository.insert_in_transaction` under one service-layer
        transaction."""
        await conn.execute(
            "INSERT INTO identities "
            "(id, user_id, provider, provider_subject, credential, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                identity_id,
                user_id,
                provider,
                provider_subject,
                credential,
                created_at,
            ),
        )

    async def insert(
        self,
        *,
        identity_id: IdentityId,
        user_id: UserId,
        provider: ProviderName,
        provider_subject: str,
        credential: PasswordHash | None,
    ) -> None:
        async with self._db.write() as conn:
            await self.insert_in_transaction(
                conn,
                identity_id=identity_id,
                user_id=user_id,
                provider=provider,
                provider_subject=provider_subject,
                credential=credential,
                created_at=now_iso(),
            )

    async def get_by_provider_subject(
        self, provider: ProviderName, provider_subject: str
    ) -> Identity | None:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT id, user_id, provider, provider_subject, credential, created_at "
            "FROM identities WHERE provider = ? AND provider_subject = ?",
            (provider, provider_subject),
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_identity(row) if row else None

    async def list_for_user(self, user_id: UserId) -> list[Identity]:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT id, user_id, provider, provider_subject, credential, created_at "
            "FROM identities WHERE user_id = ? ORDER BY created_at, id",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_identity(r) for r in rows]

    async def update_credential(
        self, identity_id: IdentityId, credential: PasswordHash
    ) -> None:
        async with self._db.write() as conn:
            await conn.execute(
                "UPDATE identities SET credential = ? WHERE id = ?",
                (credential, identity_id),
            )

    @staticmethod
    def _row_to_identity(row) -> Identity:
        iid, uid, prov, subj, cred, created = row
        return Identity(
            id=IdentityId(iid),
            user_id=UserId(uid),
            provider=prov,
            provider_subject=subj,
            credential=PasswordHash(cred) if cred is not None else None,
            created_at=parse_dt(created),
        )


class SessionRepository:
    def __init__(self, db: AuthDb) -> None:
        self._db = db

    async def insert(
        self,
        *,
        token: SessionToken,
        user_id: UserId,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> None:
        async with self._db.write() as conn:
            now = now_iso()
            await conn.execute(
                "INSERT INTO sessions "
                "(token, user_id, created_at, expires_at, last_seen_at, "
                "user_agent, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    token,
                    user_id,
                    now,
                    expires_at.isoformat(),
                    now,
                    user_agent,
                    ip_address,
                ),
            )

    async def get(self, token: SessionToken) -> Session | None:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT token, user_id, created_at, expires_at, last_seen_at, "
            "user_agent, ip_address FROM sessions WHERE token = ?",
            (token,),
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_session(row) if row else None

    async def bump_last_seen(self, token: SessionToken) -> None:
        async with self._db.write() as conn:
            await conn.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token = ?",
                (now_iso(), token),
            )

    async def delete(self, token: SessionToken) -> None:
        async with self._db.write() as conn:
            await conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    async def delete_all_for_user(self, user_id: UserId) -> None:
        async with self._db.write() as conn:
            await conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    async def delete_expired(self, as_of: datetime) -> int:
        async with self._db.write() as conn:
            cur = await conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (as_of.isoformat(),),
            )
            return cur.rowcount

    async def list_for_user(self, user_id: UserId) -> list[Session]:
        conn = await self._db.conn()
        async with conn.execute(
            "SELECT token, user_id, created_at, expires_at, last_seen_at, "
            "user_agent, ip_address FROM sessions WHERE user_id = ? "
            "ORDER BY created_at, token",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_session(r) for r in rows]

    @staticmethod
    def _row_to_session(row) -> Session:
        tok, uid, created, expires, last_seen, ua, ip = row
        return Session(
            token=SessionToken(tok),
            user_id=UserId(uid),
            created_at=parse_dt(created),
            expires_at=parse_dt(expires),
            last_seen_at=parse_dt(last_seen),
            user_agent=ua,
            ip_address=ip,
        )


class SetupRepository:
    def __init__(self, db: AuthDb) -> None:
        self._db = db

    async def get(self, key: str) -> str | None:
        conn = await self._db.conn()
        async with conn.execute("SELECT value FROM setup WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def put(self, key: str, value: str) -> None:
        async with self._db.write() as conn:
            await conn.execute(
                "INSERT INTO setup (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    async def delete(self, key: str) -> None:
        async with self._db.write() as conn:
            await conn.execute("DELETE FROM setup WHERE key = ?", (key,))

    async def get_in_transaction(
        self, txn: aiosqlite.Connection, key: str
    ) -> str | None:
        async with txn.execute("SELECT value FROM setup WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def delete_in_transaction(self, txn: aiosqlite.Connection, key: str) -> None:
        await txn.execute("DELETE FROM setup WHERE key = ?", (key,))
