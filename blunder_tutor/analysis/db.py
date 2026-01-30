from __future__ import annotations

import sqlite3
from pathlib import Path

import aiosqlite


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(db_path)

    conn = sqlite3.connect(
        db_path_str,
        check_same_thread=False,
        timeout=30.0,
    )

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")

    return conn


async def _connect_async(db_path: Path) -> aiosqlite.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(db_path)

    conn = await aiosqlite.connect(db_path_str, timeout=30.0)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute("PRAGMA busy_timeout=30000;")

    return conn
