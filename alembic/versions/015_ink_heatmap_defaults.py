"""Move stored default heatmap colours to the ink ramp.

Revision ID: 015
Revises: 014
Create Date: 2026-11-08

The dashboard keeps green for "better than before", so the puzzle-activity
heatmap's green default gave green a second meaning. Saving the theme in
Settings persists every key, so most installs store the old greens verbatim.
Only exact matches of the old defaults are rewritten; a colour the user picked
stays.
"""

from __future__ import annotations

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None

OLD_TO_NEW = (
    ("theme_heatmap_l1", "#B8D9CA", "#BFB9AC"),
    ("theme_heatmap_l2", "#5BAA7D", "#8F8A7E"),
    ("theme_heatmap_l3", "#2D8F3E", "#57534A"),
    ("theme_heatmap_l4", "#1A6B2A", "#1A1A1A"),
)


def upgrade() -> None:
    for key, old, new in OLD_TO_NEW:
        op.execute(
            f"UPDATE app_settings SET value = '{new}' WHERE key = '{key}' AND upper(value) = '{old}'"
        )


def downgrade() -> None:
    for key, old, new in OLD_TO_NEW:
        op.execute(
            f"UPDATE app_settings SET value = '{old}' WHERE key = '{key}' AND upper(value) = '{new}'"
        )
