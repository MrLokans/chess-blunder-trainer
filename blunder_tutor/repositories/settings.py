from __future__ import annotations

from datetime import datetime

from blunder_tutor.features import DEFAULTS, Feature
from blunder_tutor.repositories.base import BaseDbRepository


class SettingsRepository(BaseDbRepository):
    async def ensure_settings_table(self) -> None:
        conn = await self.get_connection()
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO app_settings (key, value) VALUES
                ('setup_completed', 'false'),
                ('lichess_username', NULL),
                ('chesscom_username', NULL);
            """
        )
        await conn.commit()

    async def get_setting(self, key: str) -> str | None:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def set_setting(self, key: str, value: str | None) -> None:
        conn = await self.get_connection()
        await conn.execute(
            """
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, datetime.utcnow().isoformat()),
        )
        await conn.commit()

    async def get_all_settings(self) -> dict[str, str]:
        conn = await self.get_connection()
        async with conn.execute("SELECT key, value FROM app_settings") as cursor:
            rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows if row[1] is not None}

    async def is_setup_completed(self) -> bool:
        value = await self.get_setting("setup_completed")
        return value == "true"

    async def mark_setup_completed(self) -> None:
        await self.set_setting("setup_completed", "true")

    async def get_feature_flags(self) -> dict[str, bool]:
        all_settings = await self.get_all_settings()
        result = {}
        for feature in Feature:
            db_val = all_settings.get(f"feature_{feature.value}")
            result[feature.value] = (
                db_val == "true" if db_val is not None else DEFAULTS[feature]
            )
        return result

    async def set_feature_flags(self, flags: dict[str, bool]) -> None:
        for key, enabled in flags.items():
            if Feature.is_valid(key):
                await self.set_setting(f"feature_{key}", "true" if enabled else "false")

    async def get_configured_usernames(self) -> dict[str, str]:
        usernames = {}
        lichess = await self.get_setting("lichess_username")
        chesscom = await self.get_setting("chesscom_username")

        if lichess:
            usernames["lichess"] = lichess
        if chesscom:
            usernames["chesscom"] = chesscom

        return usernames
