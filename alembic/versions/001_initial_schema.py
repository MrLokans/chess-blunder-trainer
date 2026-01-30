"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-30

This migration creates the complete initial schema including all tables,
indexes, views, and the inline migrations that were previously applied
dynamically in ensure_schema().
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_games",
        sa.Column("game_id", sa.Text(), primary_key=True),
        sa.Column("pgn_path", sa.Text(), nullable=False),
        sa.Column("analyzed_at", sa.Text(), nullable=False),
        sa.Column("engine_path", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=True),
        sa.Column("time_limit", sa.Float(), nullable=True),
        sa.Column("inaccuracy", sa.Integer(), nullable=False),
        sa.Column("mistake", sa.Integer(), nullable=False),
        sa.Column("blunder", sa.Integer(), nullable=False),
        sa.Column("eco_code", sa.Text(), nullable=True),
        sa.Column("eco_name", sa.Text(), nullable=True),
    )
    op.create_index("idx_analysis_games_eco", "analysis_games", ["eco_code"])

    op.create_table(
        "analysis_moves",
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("player", sa.Integer(), nullable=False),
        sa.Column("uci", sa.Text(), nullable=False),
        sa.Column("san", sa.Text(), nullable=True),
        sa.Column("eval_before", sa.Integer(), nullable=False),
        sa.Column("eval_after", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("cp_loss", sa.Integer(), nullable=False),
        sa.Column("classification", sa.Integer(), nullable=False),
        sa.Column("best_move_uci", sa.Text(), nullable=True),
        sa.Column("best_move_san", sa.Text(), nullable=True),
        sa.Column("best_line", sa.Text(), nullable=True),
        sa.Column("best_move_eval", sa.Integer(), nullable=True),
        sa.Column("game_phase", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("game_id", "ply"),
        sa.ForeignKeyConstraint(["game_id"], ["analysis_games.game_id"]),
    )
    op.create_index("idx_analysis_moves_game", "analysis_moves", ["game_id"])
    op.create_index("idx_analysis_moves_class", "analysis_moves", ["classification"])
    op.create_index("idx_analysis_moves_cpl", "analysis_moves", ["cp_loss"])
    op.create_index("idx_analysis_moves_phase", "analysis_moves", ["game_phase"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.Text(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value) VALUES
            ('setup_completed', 'false'),
            ('lichess_username', NULL),
            ('chesscom_username', NULL),
            ('auto_sync_enabled', 'false'),
            ('sync_interval_hours', '24'),
            ('last_sync_timestamp', NULL),
            ('sync_max_games', '1000'),
            ('analyze_new_games_automatically', 'true'),
            ('spaced_repetition_days', '30')
        """
    )

    op.create_table(
        "puzzle_attempts",
        sa.Column("attempt_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("was_correct", sa.Integer(), nullable=False),
        sa.Column("user_move_uci", sa.Text(), nullable=True),
        sa.Column("best_move_uci", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["analysis_games.game_id"]),
    )
    op.create_index("idx_attempts_game_ply", "puzzle_attempts", ["game_id", "ply"])
    op.create_index("idx_attempts_username", "puzzle_attempts", ["username"])
    op.create_index(
        "idx_attempts_correct", "puzzle_attempts", ["was_correct", "attempted_at"]
    )
    op.create_index(
        "idx_attempts_composite",
        "puzzle_attempts",
        ["game_id", "ply", "was_correct", "attempted_at"],
    )

    op.create_table(
        "background_jobs",
        sa.Column("job_id", sa.Text(), primary_key=True),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Text(), nullable=True),
        sa.Column("end_date", sa.Text(), nullable=True),
        sa.Column("max_games", sa.Integer(), nullable=True),
        sa.Column("progress_current", sa.Integer(), server_default="0"),
        sa.Column("progress_total", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
    )
    op.create_index("idx_jobs_status", "background_jobs", ["status"])
    op.create_index("idx_jobs_created", "background_jobs", ["created_at"], unique=False)
    op.create_index("idx_jobs_type", "background_jobs", ["job_type"])

    op.create_table(
        "game_index_cache",
        sa.Column("game_id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("white", sa.Text(), nullable=True),
        sa.Column("black", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("date", sa.Text(), nullable=True),
        sa.Column("end_time_utc", sa.Text(), nullable=True),
        sa.Column("time_control", sa.Text(), nullable=True),
        sa.Column("pgn_content", sa.Text(), nullable=False),
        sa.Column("analyzed", sa.Integer(), server_default="0"),
        sa.Column("indexed_at", sa.Text(), nullable=False),
    )
    op.create_index("idx_game_cache_source", "game_index_cache", ["source"])
    op.create_index("idx_game_cache_username", "game_index_cache", ["username"])
    op.create_index("idx_game_cache_date", "game_index_cache", ["end_time_utc"])
    op.create_index("idx_game_cache_analyzed", "game_index_cache", ["analyzed"])
    op.create_index(
        "idx_game_cache_composite",
        "game_index_cache",
        ["source", "username", "end_time_utc"],
    )

    op.create_table(
        "analysis_step_status",
        sa.Column("game_id", sa.Text(), nullable=False),
        sa.Column("step_id", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("game_id", "step_id"),
    )
    op.create_index("idx_step_status_game", "analysis_step_status", ["game_id"])

    op.execute(
        """
        CREATE VIEW IF NOT EXISTS game_statistics AS
        SELECT
            g.source,
            g.username,
            COUNT(*) as total_games,
            SUM(CASE WHEN g.analyzed = 1 THEN 1 ELSE 0 END) as analyzed_games,
            COUNT(*) - SUM(CASE WHEN g.analyzed = 1 THEN 1 ELSE 0 END) as pending_games,
            MIN(g.end_time_utc) as oldest_game_date,
            MAX(g.end_time_utc) as newest_game_date,
            SUM(CASE WHEN g.analyzed = 1 AND g.end_time_utc >= date('now', '-30 days') THEN 1 ELSE 0 END) as analyzed_last_30_days
        FROM game_index_cache g
        GROUP BY g.source, g.username
        """
    )

    op.execute(
        """
        CREATE VIEW IF NOT EXISTS blunder_statistics AS
        SELECT
            am.game_id,
            g.source,
            g.username,
            g.end_time_utc,
            COUNT(*) as blunder_count,
            AVG(am.cp_loss) as avg_cp_loss
        FROM analysis_moves am
        JOIN game_index_cache g ON am.game_id = g.game_id
        WHERE am.classification = 3
        GROUP BY am.game_id, g.source, g.username, g.end_time_utc
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS blunder_statistics")
    op.execute("DROP VIEW IF EXISTS game_statistics")

    op.drop_table("analysis_step_status")
    op.drop_table("game_index_cache")
    op.drop_table("background_jobs")
    op.drop_table("puzzle_attempts")
    op.drop_table("app_settings")
    op.drop_table("analysis_moves")
    op.drop_table("analysis_games")
