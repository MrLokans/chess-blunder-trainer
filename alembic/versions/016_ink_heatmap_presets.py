"""Move stored Ocean and Forest heatmap colours to their ink ramps.

Revision ID: 016
Revises: 015
Create Date: 2026-11-08

Like 015 for the default theme: the Ocean and Forest presets drew the
puzzle-activity heatmap in their success hue, giving it a second meaning.
Applying a preset stores its colours, so only exact matches of the old preset
values are rewritten; a colour the user picked stays.
"""

from __future__ import annotations

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

OLD_TO_NEW = (
    # Ocean
    ("theme_heatmap_empty", "#D6E8E0", "#E0E7E4"),
    ("theme_heatmap_l1", "#7DD3C0", "#B1B9BB"),
    ("theme_heatmap_l2", "#2A9D8F", "#7F888F"),
    ("theme_heatmap_l3", "#1A7A6E", "#45505C"),
    ("theme_heatmap_l4", "#0F5A52", "#0A1628"),
    # Forest
    ("theme_heatmap_empty", "#D8E8DC", "#E6E5DF"),
    ("theme_heatmap_l1", "#95D5B2", "#BABDB6"),
    ("theme_heatmap_l2", "#52B788", "#8A9289"),
    ("theme_heatmap_l3", "#2D6A4F", "#536055"),
    ("theme_heatmap_l4", "#1B4332", "#1B2E20"),
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
