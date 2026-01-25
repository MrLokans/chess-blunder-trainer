from __future__ import annotations

from datetime import datetime
from pathlib import Path

from blunder_tutor.analysis.db import _connect
from blunder_tutor.index import read_index


def migrate_index_to_cache(data_dir: Path, verbose: bool = True) -> int:
    db_path = data_dir / "analysis" / "analysis.sqlite"
    conn = _connect(db_path)

    # Get set of analyzed game IDs
    analyzed_games = set()
    with conn:
        rows = conn.execute("SELECT game_id FROM analysis_games").fetchall()
        analyzed_games = {row[0] for row in rows}

    # Read all records from JSONL index
    total = 0
    inserted = 0
    skipped = 0

    if verbose:
        print("Reading JSONL index...")

    for record in read_index(data_dir):
        total += 1
        game_id = record.get("id")
        if not game_id:
            skipped += 1
            continue

        # Check if already in cache
        with conn:
            existing = conn.execute(
                "SELECT 1 FROM game_index_cache WHERE game_id = ? LIMIT 1",
                (game_id,),
            ).fetchone()

            if existing:
                skipped += 1
                continue

            # Insert into cache
            analyzed = 1 if game_id in analyzed_games else 0
            source = record.get("source")
            username = record.get("username")
            white = record.get("white")
            black = record.get("black")
            result = record.get("result")
            date = record.get("date")
            end_time_utc = record.get("end_time_utc")
            time_control = record.get("time_control")
            pgn_path = record.get("pgn_path")

            conn.execute(
                """
                INSERT INTO game_index_cache (
                    game_id, source, username, white, black, result,
                    date, end_time_utc, time_control, pgn_path,
                    analyzed, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    source,
                    username,
                    white,
                    black,
                    result,
                    date,
                    end_time_utc,
                    time_control,
                    pgn_path,
                    analyzed,
                    datetime.utcnow().isoformat(),
                ),
            )
            inserted += 1

    conn.close()

    if verbose:
        print("Migration complete!")
        print(f"  Total records: {total}")
        print(f"  Inserted: {inserted}")
        print(f"  Skipped: {skipped}")

    return inserted


def main() -> None:
    """Command-line entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate game index from JSONL to SQLite cache"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory (default: data)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    migrate_index_to_cache(args.data_dir, verbose=not args.quiet)


if __name__ == "__main__":
    main()
