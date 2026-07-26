from __future__ import annotations

from pathlib import Path

import aiosqlite

# `PRAGMA user_version` migration ladder: entry N upgrades version N -> N+1.
# Future billing schema changes are one appended entry — never edit an
# existing one on a released version.
_MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE subscriptions (
        user_id                 TEXT PRIMARY KEY,
        stripe_customer_id      TEXT UNIQUE,
        stripe_subscription_id  TEXT UNIQUE,
        status                  TEXT NOT NULL,
        plan                    TEXT,
        trial_ends_at           TEXT NOT NULL,
        current_period_end      TEXT,
        created_at              TEXT NOT NULL,
        updated_at              TEXT NOT NULL
    );
    CREATE INDEX subscriptions_customer_idx
        ON subscriptions(stripe_customer_id);

    CREATE TABLE webhook_events (
        event_id     TEXT PRIMARY KEY,
        received_at  TEXT NOT NULL
    );

    CREATE TABLE user_nodes (
        user_id  TEXT PRIMARY KEY,
        node_id  TEXT NOT NULL
    );
    """,
)


async def initialize_billing_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("PRAGMA user_version") as cur:
            row = await cur.fetchone()
        version = row[0] if row else 0
        for index, migration in enumerate(_MIGRATIONS):
            if index < version:
                continue
            await conn.executescript(migration)
            await conn.execute(f"PRAGMA user_version = {index + 1}")
        await conn.commit()
