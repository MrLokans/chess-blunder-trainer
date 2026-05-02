from __future__ import annotations

from datetime import datetime

from blunder_tutor.features import DEFAULTS, Feature
from blunder_tutor.repositories.base import BaseDbRepository


class SettingsRepository(BaseDbRepository):
    async def ensure_settings_table(self) -> None:
        async with self.write_transaction() as conn:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO app_settings (key, value) VALUES
                    ('setup_completed', 'false');
                """
            )

    async def read_setting(self, key: str) -> str | None:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def write_setting(self, key: str, value: str | None) -> None:
        async with self.write_transaction() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, value, datetime.utcnow().isoformat()),
            )

    async def get_all_settings(self) -> dict[str, str]:
        conn = await self.get_connection()
        async with conn.execute("SELECT key, value FROM app_settings") as cursor:
            rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows if row[1] is not None}

    async def is_setup_completed(self) -> bool:
        value = await self.read_setting("setup_completed")
        return value == "true"

    async def mark_setup_completed(self) -> None:
        await self.write_setting("setup_completed", "true")

    async def read_feature_flags(self) -> dict[str, bool]:
        all_settings = await self.get_all_settings()
        result = {}
        for feature in Feature:
            db_val = all_settings.get(f"feature_{feature.value}")
            result[feature.value] = (
                db_val == "true" if db_val is not None else DEFAULTS[feature]
            )
        return result

    async def write_feature_flags(self, flags: dict[str, bool]) -> None:
        for key, enabled in flags.items():
            if Feature.is_valid(key):
                await self.write_setting(
                    f"feature_{key}", "true" if enabled else "false"
                )

    async def get_configured_usernames(self) -> dict[str, str]:
        usernames = {}
        lichess = await self.read_setting("lichess_username")
        chesscom = await self.read_setting("chesscom_username")

        if lichess:
            usernames["lichess"] = lichess
        if chesscom:
            usernames["chesscom"] = chesscom

        return usernames
