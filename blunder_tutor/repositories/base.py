from __future__ import annotations

from pathlib import Path
from typing import Self

import aiosqlite

from blunder_tutor.analysis.db import _connect_async
from blunder_tutor.web.config import AppConfig


class BaseDbRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def get_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await _connect_async(self.db_path)
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @classmethod
    def from_config(cls, config: AppConfig) -> Self:
        return cls(db_path=config.data.db_path)
