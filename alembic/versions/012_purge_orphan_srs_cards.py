"""Delete srs_cards whose game no longer exists.

Revision ID: 012
Revises: 011
Create Date: 2026-10-22

Profile delete with games did not cascade to srs_cards, so orphan cards made
`/api/srs/next` return 500 and inflated the due count. Irreversible: the
orphans point at games that are already gone.
"""

from __future__ import annotations

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM srs_cards
        WHERE game_id NOT IN (SELECT game_id FROM game_index_cache)
        """
    )


def downgrade() -> None:
    pass
