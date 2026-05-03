from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Self

import aiosqlite

from blunder_tutor.analysis.db import _connect_async
from blunder_tutor.web.config import AppConfig


class BaseDbRepository:
    _write_locks: dict[str, asyncio.Lock] = {}

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        # Concurrent callers (e.g. `asyncio.gather(repo.foo(), repo.bar())`)
        # would otherwise both pass the `_conn is None` check, both open a
        # connection, and orphan one of them — surfacing as an aiosqlite
        # ResourceWarning at GC time. Double-checked locking serializes the
        # cold-path open without paying for the lock on warm reads.
        self._conn_lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @classmethod
    def from_config(cls, config: AppConfig) -> Self:
        return cls(db_path=config.data.db_path)

    async def get_connection(self) -> aiosqlite.Connection:
        if self._conn is not None:
            return self._conn
        async with self._conn_lock:
            if self._conn is None:
                self._conn = await _connect_async(self.db_path)
            return self._conn

    @asynccontextmanager
    async def write_transaction(self) -> AsyncGenerator[aiosqlite.Connection]:
        lock = self._get_write_lock(self.db_path)
        async with lock:
            conn = await self.get_connection()
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @classmethod
    def _get_write_lock(cls, db_path: Path) -> asyncio.Lock:
        key = str(db_path.resolve())
        if key not in cls._write_locks:
            cls._write_locks[key] = asyncio.Lock()
        return cls._write_locks[key]
