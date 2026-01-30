from __future__ import annotations

import sqlite3
from pathlib import Path

import aiosqlite


def _connect(db_path: Path) -> sqlite3.Connection:
    """Create a thread-safe SQLite connection with proper settings for concurrent access.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        SQLite connection configured for multi-threaded access
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to string to ensure compatibility
    db_path_str = str(db_path)

    # Create connection with multi-threading support
    # check_same_thread=False allows the connection to be used from different threads
    # timeout=30 gives other threads time to finish their operations
    conn = sqlite3.connect(
        db_path_str,
        check_same_thread=False,  # Allow multi-threaded access
        timeout=30.0,  # Wait up to 30 seconds if database is locked
    )

    # Enable WAL mode for better concurrency (multiple readers, one writer)
    conn.execute("PRAGMA journal_mode=WAL;")

    # Use NORMAL synchronous mode for better performance
    conn.execute("PRAGMA synchronous=NORMAL;")

    # Set busy timeout at the connection level as well
    conn.execute("PRAGMA busy_timeout=30000;")  # 30 seconds in milliseconds

    return conn


def ensure_schema(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_games (
                game_id TEXT PRIMARY KEY,
                pgn_path TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                engine_path TEXT NOT NULL,
                depth INTEGER,
                time_limit REAL,
                inaccuracy INTEGER NOT NULL,
                mistake INTEGER NOT NULL,
                blunder INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_moves (
                game_id TEXT NOT NULL,
                ply INTEGER NOT NULL,
                move_number INTEGER NOT NULL,
                player INTEGER NOT NULL,
                uci TEXT NOT NULL,
                san TEXT,
                eval_before INTEGER NOT NULL,
                eval_after INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                cp_loss INTEGER NOT NULL,
                classification INTEGER NOT NULL,
                best_move_uci TEXT,
                best_move_san TEXT,
                best_line TEXT,
                best_move_eval INTEGER,
                PRIMARY KEY (game_id, ply),
                FOREIGN KEY (game_id) REFERENCES analysis_games (game_id)
            );
            CREATE INDEX IF NOT EXISTS idx_analysis_moves_game
                ON analysis_moves (game_id);
            CREATE INDEX IF NOT EXISTS idx_analysis_moves_class
                ON analysis_moves (classification);
            CREATE INDEX IF NOT EXISTS idx_analysis_moves_cpl
                ON analysis_moves (cp_loss);
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO app_settings (key, value) VALUES
                ('setup_completed', 'false'),
                ('lichess_username', NULL),
                ('chesscom_username', NULL),
                ('auto_sync_enabled', 'false'),
                ('sync_interval_hours', '24'),
                ('last_sync_timestamp', NULL),
                ('sync_max_games', '1000'),
                ('analyze_new_games_automatically', 'true'),
                ('spaced_repetition_days', '30');

            CREATE TABLE IF NOT EXISTS puzzle_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                ply INTEGER NOT NULL,
                username TEXT NOT NULL,
                was_correct INTEGER NOT NULL,
                user_move_uci TEXT,
                best_move_uci TEXT,
                attempted_at TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES analysis_games (game_id)
            );
            CREATE INDEX IF NOT EXISTS idx_attempts_game_ply ON puzzle_attempts(game_id, ply);
            CREATE INDEX IF NOT EXISTS idx_attempts_username ON puzzle_attempts(username);
            CREATE INDEX IF NOT EXISTS idx_attempts_correct ON puzzle_attempts(was_correct, attempted_at);
            CREATE INDEX IF NOT EXISTS idx_attempts_composite ON puzzle_attempts(game_id, ply, was_correct, attempted_at);

            CREATE TABLE IF NOT EXISTS background_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                username TEXT,
                source TEXT,
                start_date TEXT,
                end_date TEXT,
                max_games INTEGER,
                progress_current INTEGER DEFAULT 0,
                progress_total INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                result_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON background_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_created ON background_jobs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_type ON background_jobs(job_type);

            CREATE TABLE IF NOT EXISTS game_index_cache (
                game_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                username TEXT NOT NULL,
                white TEXT,
                black TEXT,
                result TEXT,
                date TEXT,
                end_time_utc TEXT,
                time_control TEXT,
                pgn_content TEXT NOT NULL,
                analyzed INTEGER DEFAULT 0,
                indexed_at TEXT NOT NULL,
                UNIQUE(game_id)
            );
            CREATE INDEX IF NOT EXISTS idx_game_cache_source ON game_index_cache(source);
            CREATE INDEX IF NOT EXISTS idx_game_cache_username ON game_index_cache(username);
            CREATE INDEX IF NOT EXISTS idx_game_cache_date ON game_index_cache(end_time_utc);
            CREATE INDEX IF NOT EXISTS idx_game_cache_analyzed ON game_index_cache(analyzed);
            CREATE INDEX IF NOT EXISTS idx_game_cache_composite ON game_index_cache(source, username, end_time_utc);

            CREATE TABLE IF NOT EXISTS analysis_step_status (
                game_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY (game_id, step_id)
            );
            CREATE INDEX IF NOT EXISTS idx_step_status_game ON analysis_step_status(game_id);
            """
        )

        # Create views (must be separate from main script due to IF NOT EXISTS)
        conn.execute(
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

        conn.execute(
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

        # Migration: Add best_move columns if they don't exist
        cursor = conn.execute("PRAGMA table_info(analysis_moves)")
        columns = {row[1] for row in cursor.fetchall()}

        if "best_move_uci" not in columns:
            conn.execute("ALTER TABLE analysis_moves ADD COLUMN best_move_uci TEXT")
        if "best_move_san" not in columns:
            conn.execute("ALTER TABLE analysis_moves ADD COLUMN best_move_san TEXT")
        if "best_line" not in columns:
            conn.execute("ALTER TABLE analysis_moves ADD COLUMN best_line TEXT")
        if "best_move_eval" not in columns:
            conn.execute("ALTER TABLE analysis_moves ADD COLUMN best_move_eval INTEGER")
        if "game_phase" not in columns:
            conn.execute("ALTER TABLE analysis_moves ADD COLUMN game_phase INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_moves_phase ON analysis_moves(game_phase)"
        )

        # Migration: Add ECO columns to analysis_games if they don't exist
        cursor = conn.execute("PRAGMA table_info(analysis_games)")
        games_columns = {row[1] for row in cursor.fetchall()}

        if "eco_code" not in games_columns:
            conn.execute("ALTER TABLE analysis_games ADD COLUMN eco_code TEXT")
        if "eco_name" not in games_columns:
            conn.execute("ALTER TABLE analysis_games ADD COLUMN eco_name TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_games_eco ON analysis_games(eco_code)"
        )

        # Migration: Rename pgn_path to pgn_content if needed
        cursor = conn.execute("PRAGMA table_info(game_index_cache)")
        cache_columns = {row[1] for row in cursor.fetchall()}

        if "pgn_path" in cache_columns and "pgn_content" not in cache_columns:
            conn.execute(
                "ALTER TABLE game_index_cache RENAME COLUMN pgn_path TO pgn_content"
            )


async def _connect_async(db_path: Path) -> aiosqlite.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(db_path)

    conn = await aiosqlite.connect(db_path_str, timeout=30.0)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute("PRAGMA busy_timeout=30000;")

    return conn


async def ensure_schema_async(db_path: Path) -> None:
    conn = await _connect_async(db_path)
    try:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_games (
                game_id TEXT PRIMARY KEY,
                pgn_path TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                engine_path TEXT NOT NULL,
                depth INTEGER,
                time_limit REAL,
                inaccuracy INTEGER NOT NULL,
                mistake INTEGER NOT NULL,
                blunder INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_moves (
                game_id TEXT NOT NULL,
                ply INTEGER NOT NULL,
                move_number INTEGER NOT NULL,
                player INTEGER NOT NULL,
                uci TEXT NOT NULL,
                san TEXT,
                eval_before INTEGER NOT NULL,
                eval_after INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                cp_loss INTEGER NOT NULL,
                classification INTEGER NOT NULL,
                best_move_uci TEXT,
                best_move_san TEXT,
                best_line TEXT,
                best_move_eval INTEGER,
                PRIMARY KEY (game_id, ply),
                FOREIGN KEY (game_id) REFERENCES analysis_games (game_id)
            );
            CREATE INDEX IF NOT EXISTS idx_analysis_moves_game
                ON analysis_moves (game_id);
            CREATE INDEX IF NOT EXISTS idx_analysis_moves_class
                ON analysis_moves (classification);
            CREATE INDEX IF NOT EXISTS idx_analysis_moves_cpl
                ON analysis_moves (cp_loss);
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO app_settings (key, value) VALUES
                ('setup_completed', 'false'),
                ('lichess_username', NULL),
                ('chesscom_username', NULL),
                ('auto_sync_enabled', 'false'),
                ('sync_interval_hours', '24'),
                ('last_sync_timestamp', NULL),
                ('sync_max_games', '1000'),
                ('analyze_new_games_automatically', 'true'),
                ('spaced_repetition_days', '30');

            CREATE TABLE IF NOT EXISTS puzzle_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                ply INTEGER NOT NULL,
                username TEXT NOT NULL,
                was_correct INTEGER NOT NULL,
                user_move_uci TEXT,
                best_move_uci TEXT,
                attempted_at TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES analysis_games (game_id)
            );
            CREATE INDEX IF NOT EXISTS idx_attempts_game_ply ON puzzle_attempts(game_id, ply);
            CREATE INDEX IF NOT EXISTS idx_attempts_username ON puzzle_attempts(username);
            CREATE INDEX IF NOT EXISTS idx_attempts_correct ON puzzle_attempts(was_correct, attempted_at);
            CREATE INDEX IF NOT EXISTS idx_attempts_composite ON puzzle_attempts(game_id, ply, was_correct, attempted_at);

            CREATE TABLE IF NOT EXISTS background_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                username TEXT,
                source TEXT,
                start_date TEXT,
                end_date TEXT,
                max_games INTEGER,
                progress_current INTEGER DEFAULT 0,
                progress_total INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                result_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON background_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_created ON background_jobs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_type ON background_jobs(job_type);

            CREATE TABLE IF NOT EXISTS game_index_cache (
                game_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                username TEXT NOT NULL,
                white TEXT,
                black TEXT,
                result TEXT,
                date TEXT,
                end_time_utc TEXT,
                time_control TEXT,
                pgn_content TEXT NOT NULL,
                analyzed INTEGER DEFAULT 0,
                indexed_at TEXT NOT NULL,
                UNIQUE(game_id)
            );
            CREATE INDEX IF NOT EXISTS idx_game_cache_source ON game_index_cache(source);
            CREATE INDEX IF NOT EXISTS idx_game_cache_username ON game_index_cache(username);
            CREATE INDEX IF NOT EXISTS idx_game_cache_date ON game_index_cache(end_time_utc);
            CREATE INDEX IF NOT EXISTS idx_game_cache_analyzed ON game_index_cache(analyzed);
            CREATE INDEX IF NOT EXISTS idx_game_cache_composite ON game_index_cache(source, username, end_time_utc);

            CREATE TABLE IF NOT EXISTS analysis_step_status (
                game_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY (game_id, step_id)
            );
            CREATE INDEX IF NOT EXISTS idx_step_status_game ON analysis_step_status(game_id);
            """
        )

        await conn.execute(
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

        await conn.execute(
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

        async with conn.execute("PRAGMA table_info(analysis_moves)") as cursor:
            rows = await cursor.fetchall()
            columns = {row[1] for row in rows}

        if "best_move_uci" not in columns:
            await conn.execute(
                "ALTER TABLE analysis_moves ADD COLUMN best_move_uci TEXT"
            )
        if "best_move_san" not in columns:
            await conn.execute(
                "ALTER TABLE analysis_moves ADD COLUMN best_move_san TEXT"
            )
        if "best_line" not in columns:
            await conn.execute("ALTER TABLE analysis_moves ADD COLUMN best_line TEXT")
        if "best_move_eval" not in columns:
            await conn.execute(
                "ALTER TABLE analysis_moves ADD COLUMN best_move_eval INTEGER"
            )
        if "game_phase" not in columns:
            await conn.execute(
                "ALTER TABLE analysis_moves ADD COLUMN game_phase INTEGER"
            )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_moves_phase ON analysis_moves(game_phase)"
        )

        # Migration: Add ECO columns to analysis_games if they don't exist
        async with conn.execute("PRAGMA table_info(analysis_games)") as cursor:
            rows = await cursor.fetchall()
            games_columns = {row[1] for row in rows}

        if "eco_code" not in games_columns:
            await conn.execute("ALTER TABLE analysis_games ADD COLUMN eco_code TEXT")
        if "eco_name" not in games_columns:
            await conn.execute("ALTER TABLE analysis_games ADD COLUMN eco_name TEXT")
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_games_eco ON analysis_games(eco_code)"
        )

        async with conn.execute("PRAGMA table_info(game_index_cache)") as cursor:
            rows = await cursor.fetchall()
            cache_columns = {row[1] for row in rows}

        if "pgn_path" in cache_columns and "pgn_content" not in cache_columns:
            await conn.execute(
                "ALTER TABLE game_index_cache RENAME COLUMN pgn_path TO pgn_content"
            )

        await conn.commit()
    finally:
        await conn.close()
