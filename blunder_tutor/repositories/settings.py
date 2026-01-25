from __future__ import annotations

from datetime import datetime

from blunder_tutor.repositories.base import BaseDbRepository


class SettingsRepository(BaseDbRepository):
    def ensure_settings_table(self) -> None:
        with self.connection as conn:
            conn.executescript(
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

    def get_setting(self, key: str) -> str | None:
        with self.connection as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None

    def set_setting(self, key: str, value: str | None) -> None:
        conn = self.connection
        conn.execute(
            """
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, datetime.utcnow().isoformat()),
        )
        conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        with self.connection as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
            return {row[0]: row[1] for row in rows if row[1] is not None}

    def is_setup_completed(self) -> bool:
        value = self.get_setting("setup_completed")
        return value == "true"

    def mark_setup_completed(self) -> None:
        self.set_setting("setup_completed", "true")

    def get_configured_usernames(self) -> dict[str, str]:
        usernames = {}
        lichess = self.get_setting("lichess_username")
        chesscom = self.get_setting("chesscom_username")

        if lichess:
            usernames["lichess"] = lichess
        if chesscom:
            usernames["chesscom"] = chesscom

        return usernames
