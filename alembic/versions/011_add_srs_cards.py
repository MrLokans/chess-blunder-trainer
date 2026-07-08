"""Add srs_cards table for the Blunder Inbox spaced-repetition queue.

Revision ID: 011
Revises: 010
Create Date: 2026-07-07
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"

BACKFILL_WINDOW_DAYS = 60

# Enroll every (game_id, ply) whose most recent attempt inside the window
# was a failure, so existing users wake up to a meaningful inbox.
BACKFILL_SQL = """
    INSERT OR IGNORE INTO srs_cards
        (game_id, ply, rung, state, due_at, enrolled_at,
         last_reviewed_at, total_failures)
    SELECT pa.game_id, pa.ply, 0, 0, :due_at, :now, NULL,
        (SELECT COUNT(*) FROM puzzle_attempts fails
         WHERE fails.game_id = pa.game_id AND fails.ply = pa.ply
           AND fails.was_correct = 0)
    FROM puzzle_attempts pa
    JOIN (
        SELECT game_id, ply, MAX(attempted_at) AS last_at
        FROM puzzle_attempts
        GROUP BY game_id, ply
    ) latest
        ON latest.game_id = pa.game_id
       AND latest.ply = pa.ply
       AND latest.last_at = pa.attempted_at
    WHERE pa.was_correct = 0 AND pa.attempted_at >= :cutoff
"""


def upgrade() -> None:
    op.create_table(
        "srs_cards",
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("rung", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_at", sa.Text(), nullable=False),
        sa.Column("enrolled_at", sa.Text(), nullable=False),
        sa.Column("last_reviewed_at", sa.Text(), nullable=True),
        sa.Column("total_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("game_id", "ply"),
    )
    op.create_index("idx_srs_cards_due", "srs_cards", ["state", "due_at"])

    now = datetime.now(UTC)
    op.get_bind().execute(
        sa.text(BACKFILL_SQL),
        {
            "now": now.isoformat(),
            "due_at": now.isoformat(),
            "cutoff": (now - timedelta(days=BACKFILL_WINDOW_DAYS)).isoformat(),
        },
    )


def downgrade() -> None:
    op.drop_index("idx_srs_cards_due", table_name="srs_cards")
    op.drop_table("srs_cards")
