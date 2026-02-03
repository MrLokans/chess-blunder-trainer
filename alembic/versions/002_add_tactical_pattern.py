"""Add tactical pattern column to analysis_moves

Revision ID: 002
Revises: 001
Create Date: 2025-02-03

Adds tactical_pattern column to classify blunders by the tactical
motif involved (fork, pin, skewer, etc.)
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tactical_pattern column (nullable to support existing data)
    op.add_column(
        "analysis_moves",
        sa.Column("tactical_pattern", sa.Integer(), nullable=True),
    )

    # Add index for filtering by tactical pattern
    op.create_index(
        "idx_analysis_moves_tactical",
        "analysis_moves",
        ["tactical_pattern"],
    )

    # Add tactical_reason column for human-readable explanation
    op.add_column(
        "analysis_moves",
        sa.Column("tactical_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("idx_analysis_moves_tactical", table_name="analysis_moves")
    op.drop_column("analysis_moves", "tactical_pattern")
    op.drop_column("analysis_moves", "tactical_reason")
