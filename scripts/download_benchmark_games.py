#!/usr/bin/env python3
"""
Download benchmark games from Lichess for profiling.

Fetches games for a given user and saves each as an individual PGN file
under fixtures/benchmark/<username>/, suitable for filesystem-based profiling.

Usage:
    uv run python scripts/download_benchmark_games.py
    uv run python scripts/download_benchmark_games.py --username DrNykterstein --max 200
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from blunder_tutor.fetchers import lichess

BENCHMARK_DIR = Path("fixtures/benchmark")


async def download(username: str, max_games: int) -> None:
    out_dir = BENCHMARK_DIR / username.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = list(out_dir.glob("*.pgn"))
    if existing:
        print(f"Already have {len(existing)} games in {out_dir}, skipping download.")
        print("Delete the directory to re-download.")
        return

    print(f"Fetching up to {max_games} games for {username} from Lichess...")
    games, _ = await lichess.fetch(username=username, max_games=max_games)
    print(f"Fetched {len(games)} games.")

    manifest = []
    for game in games:
        pgn = game["pgn_content"]
        game_id = game["id"]
        short_id = game_id[:12]
        filename = f"{short_id}.pgn"

        (out_dir / filename).write_text(pgn, encoding="utf-8")
        manifest.append(
            {
                "filename": filename,
                "game_id": game_id,
                "white": game.get("white"),
                "black": game.get("black"),
                "result": game.get("result"),
                "date": game.get("date"),
                "time_control": game.get("time_control"),
                "source": game.get("source"),
                "username": game.get("username"),
            }
        )

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {len(manifest)} PGN files + manifest.json to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download benchmark games")
    parser.add_argument("--username", default="DrNykterstein")
    parser.add_argument("--max", type=int, default=200)
    args = parser.parse_args()
    asyncio.run(download(args.username, args.max))


if __name__ == "__main__":
    main()
