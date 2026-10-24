"""Recompute stored tactical tags of analysed blunders.

Revision ID: 013
Revises: 012
Create Date: 2026-10-24

The detector blamed a blunder for a pin the best move creates too, e.g. the self-pin
of any piece blocking a check (GH #17). Tags are recomputed in place with the current
detector rather than cleared, because the tactics backfill only runs on request and
cleared tags would drop those puzzles from pattern filters and stats. Only rows whose
tag or reason changes are written; a game whose PGN fails to replay keeps its tags.
Irreversible: the old tags were wrong.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa

from alembic import op
from blunder_tutor.background.jobs.backfill_tactics import (
    build_ply_to_board,
    classify_blunder,
)
from blunder_tutor.utils.pgn_utils import load_game_from_string

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)

_GAMES_SQL = sa.text(
    """
    SELECT DISTINCT game_id FROM analysis_moves
    WHERE classification = 3 AND tactical_pattern IS NOT NULL
    """
)
_BLUNDERS_SQL = sa.text(
    """
    SELECT am.ply, am.best_move_uci, am.tactical_pattern, am.tactical_reason,
           g.pgn_content
    FROM analysis_moves am
    JOIN game_index_cache g ON g.game_id = am.game_id
    WHERE am.game_id = :game_id AND am.classification = 3
      AND am.tactical_pattern IS NOT NULL
    """
)
_UPDATE_SQL = sa.text(
    """
    UPDATE analysis_moves SET tactical_pattern = :pattern, tactical_reason = :reason
    WHERE game_id = :game_id AND ply = :ply
    """
)


def _changed_rows(connection: sa.Connection, game_id: str) -> list[dict[str, object]]:
    blunders = connection.execute(_BLUNDERS_SQL, {"game_id": game_id}).mappings().all()
    if not blunders:
        return []
    ply_to_board = build_ply_to_board(load_game_from_string(blunders[0]["pgn_content"]))
    changed = []
    for blunder in blunders:
        update = classify_blunder(dict(blunder), ply_to_board, game_id)
        if update is None:
            continue
        pattern, reason, _, ply = update
        if (pattern, reason) != (
            blunder["tactical_pattern"],
            blunder["tactical_reason"],
        ):
            changed.append(
                {"pattern": pattern, "reason": reason, "game_id": game_id, "ply": ply}
            )
    return changed


def upgrade() -> None:
    connection = op.get_bind()
    game_ids = connection.execute(_GAMES_SQL).scalars().all()
    updated = 0
    skipped = 0
    for game_id in game_ids:
        try:
            changed = _changed_rows(connection, game_id)
        except Exception:  # noqa: BLE001 — one unreadable game must not block startup.
            logger.warning("Skipping tactics reclassification for game %s", game_id)
            skipped += 1
            continue
        if changed:
            connection.execute(_UPDATE_SQL, changed)
            updated += len(changed)
    logger.info(
        "Reclassified %d blunders across %d games (%d skipped)",
        updated,
        len(game_ids),
        skipped,
    )


def downgrade() -> None:
    pass
