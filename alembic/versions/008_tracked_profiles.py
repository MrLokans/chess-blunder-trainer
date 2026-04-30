"""Add profile, profile_preferences, profile_stats tables and game_index_cache.profile_id.

Revision ID: 008
Revises: 007
Create Date: 2026-04-30

Schema half of the tracked-platform-profiles migration. The data backfill
(legacy `lichess_username` / `chesscom_username` keys → profile rows + tagged
games) is intentionally split into the next revision so it can be reasoned
about independently of the DDL.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"

# Maps each legacy app_settings key to the platform name stored on profile rows
# and on game_index_cache.source. Order also defines profile-creation order.
_LEGACY_USERNAME_KEYS: tuple[tuple[str, str], ...] = (
    ("lichess_username", "lichess"),
    ("chesscom_username", "chesscom"),
)


def _apply_legacy_backfill(connection: sa.Connection) -> None:
    """Materialize Profile rows from legacy username settings and tag matching games.

    Idempotent by construction: `INSERT OR IGNORE` skips existing
    `(platform, username)` profiles and `(profile_id)` preferences;
    the game UPDATE only touches rows where `profile_id IS NULL`.
    Safe to re-run for repair scenarios.
    """
    for settings_key, platform in _LEGACY_USERNAME_KEYS:
        row = connection.execute(
            sa.text(
                "SELECT value FROM app_settings "
                "WHERE key = :k AND value IS NOT NULL AND value != ''"
            ),
            {"k": settings_key},
        ).fetchone()
        if row is None:
            continue
        username = row[0]
        connection.execute(
            sa.text(
                "INSERT OR IGNORE INTO profile (platform, username, is_primary) "
                "VALUES (:p, :u, 1)"
            ),
            {"p": platform, "u": username},
        )
        profile_id = connection.execute(
            sa.text(
                "SELECT id FROM profile WHERE platform = :p AND username = :u"
            ),
            {"p": platform, "u": username},
        ).scalar_one()
        connection.execute(
            sa.text(
                "INSERT OR IGNORE INTO profile_preferences (profile_id) "
                "VALUES (:pid)"
            ),
            {"pid": profile_id},
        )

    connection.execute(
        sa.text(
            "UPDATE game_index_cache SET profile_id = ("
            "    SELECT id FROM profile "
            "    WHERE profile.platform = game_index_cache.source "
            "      AND profile.username = game_index_cache.username"
            ") WHERE profile_id IS NULL"
        )
    )


def upgrade() -> None:
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.Text(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.Text(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_validated_at", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "platform IN ('lichess', 'chesscom')",
            name="ck_profile_platform",
        ),
        sa.UniqueConstraint(
            "platform", "username", name="uq_profile_platform_username"
        ),
    )
    # Partial unique index: at most one primary per platform. SQLite supports
    # WHERE-clause unique indexes natively; alembic forwards `sqlite_where`.
    op.create_index(
        "idx_profile_one_primary_per_platform",
        "profile",
        ["platform"],
        unique=True,
        sqlite_where=sa.text("is_primary = 1"),
    )

    op.create_table(
        "profile_preferences",
        sa.Column("profile_id", sa.Integer(), primary_key=True),
        sa.Column(
            "auto_sync_enabled",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("sync_max_games", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profile.id"],
            ondelete="CASCADE",
            name="fk_profile_preferences_profile_id",
        ),
    )

    op.create_table(
        "profile_stats",
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("games_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "synced_at",
            sa.Text(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("profile_id", "mode"),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profile.id"],
            ondelete="CASCADE",
            name="fk_profile_stats_profile_id",
        ),
    )

    # Raw SQL preserves the inline FK on the new column. Alembic's add_column
    # path under render_as_batch would recreate game_index_cache, which is
    # both expensive and unnecessary here.
    op.execute(
        "ALTER TABLE game_index_cache ADD COLUMN profile_id INTEGER NULL "
        "REFERENCES profile(id) ON DELETE SET NULL"
    )
    op.create_index(
        "idx_game_index_cache_profile_id",
        "game_index_cache",
        ["profile_id"],
    )

    _apply_legacy_backfill(op.get_bind())


def downgrade() -> None:
    op.drop_index(
        "idx_game_index_cache_profile_id",
        table_name="game_index_cache",
    )
    # Native DROP COLUMN avoids batch-mode recreation, which would break the
    # `game_statistics` view that references game_index_cache. SQLite 3.35+
    # (shipped with Python 3.13) supports this directly.
    op.execute("ALTER TABLE game_index_cache DROP COLUMN profile_id")

    op.drop_table("profile_stats")
    op.drop_table("profile_preferences")
    op.drop_index(
        "idx_profile_one_primary_per_platform",
        table_name="profile",
    )
    op.drop_table("profile")
