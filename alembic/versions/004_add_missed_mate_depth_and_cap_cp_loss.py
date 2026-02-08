"""Add missed_mate_depth column and cap cp_loss at 1500

Revision ID: 004
Revises: 003
Create Date: 2026-02-08

Adds missed_mate_depth (nullable integer) to analysis_moves for tracking
how many moves to mate were available when the player blundered.

Caps existing cp_loss values at 1500 to fix inflated averages caused by
mate scores being mapped to ±100,000.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

MAX_CP_LOSS = 1500


def upgrade() -> None:
    op.add_column(
        "analysis_moves",
        sa.Column("missed_mate_depth", sa.Integer(), nullable=True),
    )
    op.execute(
        f"UPDATE analysis_moves SET cp_loss = {MAX_CP_LOSS} WHERE cp_loss > {MAX_CP_LOSS}"
    )


def downgrade() -> None:
    op.drop_column("analysis_moves", "missed_mate_depth")
