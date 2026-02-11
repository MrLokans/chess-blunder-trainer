"""Add starred_puzzles table for saving favorite blunders.

Revision ID: 007
Revises: 006
Create Date: 2026-02-11
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"


def upgrade() -> None:
    op.create_table(
        "starred_puzzles",
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("starred_at", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("game_id", "ply"),
    )


def downgrade() -> None:
    op.drop_table("starred_puzzles")
