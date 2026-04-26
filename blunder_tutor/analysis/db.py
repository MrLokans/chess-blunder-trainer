from __future__ import annotations

import sqlite3
from pathlib import Path

import aiosqlite

# SQLite connection timeout for both sync and async paths. 30 s is the
# WAL-mode busy-wait ceiling — long enough to ride out routine writer
# contention, short enough that genuine deadlocks surface as errors.
SQLITE_TIMEOUT_SECONDS = 30.0
SQLITE_BUSY_TIMEOUT_MS = 30_000


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(db_path)

    conn = sqlite3.connect(
        db_path_str,
        check_same_thread=False,
        timeout=SQLITE_TIMEOUT_SECONDS,
    )

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")

    return conn


async def _connect_async(db_path: Path) -> aiosqlite.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(db_path)

    conn = await aiosqlite.connect(db_path_str, timeout=SQLITE_TIMEOUT_SECONDS)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")

    return conn
