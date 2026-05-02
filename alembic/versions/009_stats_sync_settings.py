"""Add stats_sync_interval_hours setting (default 1).

Revision ID: 009
Revises: 008
Create Date: 2026-05-01

Cadence knob for the per-profile stats sync introduced in EPIC-6 (TREK-106).
Stats sync is independent of game sync — game sync uses
`sync_interval_hours` (default 24); stats sync uses this new key
(default 1). `INSERT OR IGNORE` keeps the migration idempotent.
"""

from __future__ import annotations

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value) VALUES
            ('stats_sync_interval_hours', '1')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM app_settings WHERE key = 'stats_sync_interval_hours'")
