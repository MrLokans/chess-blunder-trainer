"""Add difficulty column to analysis_moves

Revision ID: 003
Revises: 002
Create Date: 2026-02-07

Stores a 0-100 difficulty score for each move, indicating how hard
the best move was to find (based on legal alternatives, move type, etc.)
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_moves",
        sa.Column("difficulty", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_moves", "difficulty")
