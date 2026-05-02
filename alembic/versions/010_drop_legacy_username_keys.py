"""Drop legacy lichess_username and chesscom_username settings keys.

Revision ID: 010
Revises: 009
Create Date: 2026-05-01

Final cleanup of the tracked-platform-profiles transition. Migration 008
backfilled Profile rows from these two flat settings keys, and Epic 7
(setup rewrite + Bulk Import promotion) removed the last code path that
read them: `POST /api/setup` and `GET /api/settings/usernames` are gone,
and `ImportSection` has been replaced by `BulkImportPanel`.

Pre-flight grep at land time (2026-05-01) — surviving references are all
benign:

- `alembic/versions/001_initial_schema.py` — historical seed; never re-runs
  on existing DBs.
- `alembic/versions/008_tracked_profiles.py` — the backfill that consumed
  these keys; runs before this revision.
- `blunder_tutor/repositories/settings.py` — the seed `INSERT OR IGNORE`
  for `ensure_settings_table` is being trimmed in the same change set so
  freshly-created DBs no longer carry the keys.
- `blunder_tutor/repositories/settings.py:get_configured_usernames` — still
  invoked by `sync_games._execute_legacy` and `import_game.py`'s anonymous
  fallback. After this migration both paths read None and fail closed
  (sync logs "no usernames" and exits 0/0; pgn import falls back to the
  literal "anonymous"). No behavioral regression — the legacy code paths
  themselves are slated for removal once nothing dispatches without a
  profile_id.
- `tests/profiles/test_migration.py` — tests stage at revision 007 and
  upgrade through 008, so they exercise the pre-drop state by design.

Idempotent: re-running the migration is a no-op (DELETE on missing rows).
"""

from __future__ import annotations

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM app_settings
        WHERE key IN ('lichess_username', 'chesscom_username')
        """
    )


def downgrade() -> None:
    # Restores empty-valued rows so a downgraded DB looks like the post-008
    # state. Values default to NULL because the original setup flow wrote
    # them lazily on first use; dumping real values here would be wrong.
    op.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value) VALUES
            ('lichess_username', NULL),
            ('chesscom_username', NULL)
        """
    )
