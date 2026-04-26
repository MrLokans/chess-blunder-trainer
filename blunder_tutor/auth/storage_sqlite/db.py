from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Self

import aiosqlite


class AuthDb:
    """Owns a single aiosqlite connection to ``auth.sqlite3`` plus an
    asyncio write lock that all repositories share.

    The write lock groups *multi-statement transactions* atomically —
    aiosqlite already serializes individual statements on one connection
    through its worker thread, so ``write()`` (single-statement) is
    grouped for symmetry rather than correctness: every mutation path
    traverses the same seam, so ``write()`` cannot interleave with a
    ``transaction()`` span. ``PRAGMA foreign_keys = ON`` is set exactly
    once per connection lifetime; reconnect after ``close`` re-applies it.

    Repositories accept an :class:`AuthDb` and use ``conn`` for reads and
    ``write()`` / ``transaction()`` for writes.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.path)
            await self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def conn(self) -> aiosqlite.Connection:
        return await self.connect()

    @asynccontextmanager
    async def write(self) -> AsyncIterator[aiosqlite.Connection]:
        """Single-statement write — still grabs the lock so it cannot
        interleave with a multi-statement transaction."""
        async with self._write_lock:
            conn = await self.connect()
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Multi-statement transaction (``BEGIN IMMEDIATE`` … ``COMMIT``).

        Use this for any service-layer operation that touches more than
        one table or row and must be atomic (e.g. ``register`` inserting
        ``users`` + ``identities``).
        """
        async with self._write_lock:
            conn = await self.connect()
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
