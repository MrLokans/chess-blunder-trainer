"""Canonical raw-row seeders for the ``game_index_cache`` table.

The rating-history, elo-emission, and profile suites all need to plant a
game row directly (the public ingest path runs the full fetch/index
pipeline, which these tests deliberately bypass). Before this module each
file carried its own ``_insert_game`` with a hand-written column list, so
a schema change broke them one at a time and the copies drifted (some
parametrized ``time_control``, some hard-coded it). This is the single
column list to maintain.

Prefer a repository's public API (``SqliteProfileRepository.create``,
``PuzzleAttemptRepository.record_attempt``, …) whenever one exists — reach
for these raw seeders only for ``game_index_cache`` rows, which have no
direct public insert outside the indexing pipeline.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from blunder_tutor.utils.time_control import GameType


def make_pgn(
    *,
    white: str,
    black: str,
    white_elo: int | str = "?",
    black_elo: int | str = "?",
    result: str = "*",
) -> str:
    return (
        f'[White "{white}"]\n[Black "{black}"]\n'
        f'[WhiteElo "{white_elo}"]\n[BlackElo "{black_elo}"]\n'
        f'[Result "{result}"]\n\n*\n'
    )


def insert_game_index_row(
    db: Path,
    *,
    game_id: str,
    username: str = "alice",
    source: str = "lichess",
    white: str | None = None,
    black: str = "opponent",
    result: str = "*",
    date: str = "2026-01-01",
    end_time_utc: str = "2026-01-01T00:00:00",
    time_control: str = "300",
    pgn_content: str = "1.e4 e5",
    indexed_at: str = "2026-01-01",
    game_type: int = int(GameType.BLITZ),
    profile_id: int | None = None,
    analyzed: int = 0,
) -> None:
    """Insert one ``game_index_cache`` row. ``white`` defaults to
    ``username``. Pass ``pgn_content=make_pgn(...)`` when the test reads
    ELO tags out of the PGN (rating-history); the default placeholder PGN
    is enough for tests that only need the row to exist.
    """
    with closing(sqlite3.connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO game_index_cache "
            "(game_id, source, username, white, black, result, date, "
            " end_time_utc, time_control, pgn_content, analyzed, "
            " indexed_at, game_type, profile_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                game_id,
                source,
                username,
                white if white is not None else username,
                black,
                result,
                date,
                end_time_utc,
                time_control,
                pgn_content,
                analyzed,
                indexed_at,
                game_type,
                profile_id,
            ),
        )
        conn.commit()
