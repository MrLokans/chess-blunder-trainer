"""Add trap_matches table for tracking opening trap detection.

Revision ID: 005
Revises: 004
Create Date: 2026-02-08
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trap_matches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("trap_id", sa.Text(), nullable=False),
        sa.Column("match_type", sa.Text(), nullable=False),
        sa.Column("victim_side", sa.Text(), nullable=False),
        sa.Column("user_was_victim", sa.Integer(), nullable=False),
        sa.Column("mistake_ply", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.Text(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("game_id", "trap_id"),
    )
    op.create_index("ix_trap_matches_trap_id", "trap_matches", ["trap_id"])
    op.create_index("ix_trap_matches_game_id", "trap_matches", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_trap_matches_game_id")
    op.drop_index("ix_trap_matches_trap_id")
    op.drop_table("trap_matches")
