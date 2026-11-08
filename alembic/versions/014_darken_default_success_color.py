"""Move a stored default success colour to the darker accessible default.

Revision ID: 014
Revises: 013
Create Date: 2026-11-08

The old default #2D8F3E failed WCAG AA as a button fill with either light or dark
text and as text on the page surface. Saving the theme in Settings persists every
key, so most installs store the old default verbatim and would never see the new
#247A33 default. Only an exact match is rewritten; a colour the user picked stays.
"""

from __future__ import annotations

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE app_settings SET value = '#247A33'
        WHERE key = 'theme_success' AND upper(value) = '#2D8F3E'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE app_settings SET value = '#2D8F3E'
        WHERE key = 'theme_success' AND value = '#247A33'
        """
    )
