"""Add game_type column to game_index_cache for efficient SQL-side filtering.

Revision ID: 006
Revises: 005
Create Date: 2026-02-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"


def upgrade() -> None:
    op.add_column(
        "game_index_cache",
        sa.Column("game_type", sa.Integer(), nullable=True),
    )
    op.create_index("idx_game_cache_game_type", "game_index_cache", ["game_type"])

    conn = op.get_bind()

    rows = conn.execute(
        sa.text("SELECT game_id, time_control FROM game_index_cache")
    ).fetchall()

    from blunder_tutor.utils.time_control import classify_game_type

    for game_id, time_control in rows:
        gt = int(classify_game_type(time_control))
        conn.execute(
            sa.text("UPDATE game_index_cache SET game_type = :gt WHERE game_id = :gid"),
            {"gt": gt, "gid": game_id},
        )


def downgrade() -> None:
    op.drop_index("idx_game_cache_game_type", table_name="game_index_cache")
    op.drop_column("game_index_cache", "game_type")
