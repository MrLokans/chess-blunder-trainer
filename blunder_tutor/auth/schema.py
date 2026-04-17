from __future__ import annotations

from pathlib import Path

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE,
    email        TEXT UNIQUE,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at   TEXT
);

CREATE TABLE IF NOT EXISTS identities (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider          TEXT NOT NULL,
    provider_subject  TEXT NOT NULL,
    credential        TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider, provider_subject)
);

CREATE INDEX IF NOT EXISTS identities_user_id_idx ON identities(user_id);

CREATE TABLE IF NOT EXISTS sessions (
    token         TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at    TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL DEFAULT (datetime('now')),
    user_agent    TEXT,
    ip_address    TEXT
);

CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS setup (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""


async def initialize_auth_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
