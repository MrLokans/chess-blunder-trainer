from __future__ import annotations

from pathlib import Path

import httpx
from tqdm import tqdm

from blunder_tutor.storage import index_stored_games, store_pgn

CHESSCOM_BASE_URL = "https://api.chess.com"


def fetch(
    username: str,
    data_dir: Path,
    max_games: int | None = None,
    progress_callback: callable | None = None,
) -> tuple[int, int]:
    api_username = username.lower()
    archives_url = f"{CHESSCOM_BASE_URL}/pub/player/{api_username}/games/archives"
    response = httpx.get(archives_url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    archives = response.json().get("archives", [])

    stored = 0
    skipped = 0
    total_archives = len(archives)
    remaining = max_games
    metadata_batch: list[dict[str, object]] = []

    with (
        tqdm(
            desc="Chess.com archives", total=total_archives, unit="archive"
        ) as archive_bar,
        tqdm(desc="Chess.com games", total=max_games, unit="game") as game_bar,
    ):
        for archive_url in reversed(archives):
            month_resp = httpx.get(archive_url, timeout=60, follow_redirects=True)
            month_resp.raise_for_status()
            games = month_resp.json().get("games", [])
            for game in games:
                pgn_text = game.get("pgn")
                if not pgn_text:
                    continue
                result = store_pgn("chesscom", username, pgn_text, data_dir)
                if result is None:
                    skipped += 1
                else:
                    stored += 1
                    _path, metadata = result
                    metadata_batch.append(metadata)
                game_bar.update(1)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(stored + skipped, max_games or (stored + skipped))
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        # Index all games before returning
                        index_stored_games(data_dir, metadata_batch)
                        return stored, skipped
            archive_bar.update(1)

    # Index all games at the end
    index_stored_games(data_dir, metadata_batch)
    return stored, skipped
