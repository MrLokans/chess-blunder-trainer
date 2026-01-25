from __future__ import annotations

import io
from collections.abc import Iterable
from pathlib import Path

import chess.pgn
import httpx
from tqdm import tqdm

from blunder_tutor.storage import index_stored_games, store_pgn
from blunder_tutor.utils.date_utils import parse_pgn_datetime_ms

LICHESS_BASE_URL = "https://lichess.org"


def _split_pgn_stream(pgn_text: str) -> Iterable[tuple[str, int | None]]:
    stream = io.StringIO(pgn_text)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        buffer = io.StringIO()
        print(game, file=buffer, end="\n\n")
        date = game.headers.get("UTCDate") or game.headers.get("Date")
        time = game.headers.get("UTCTime") or game.headers.get("Time")
        yield buffer.getvalue(), parse_pgn_datetime_ms(date, time)


def fetch(
    username: str,
    data_dir: Path,
    max_games: int | None = None,
    batch_size: int = 200,
    progress_callback: callable | None = None,
) -> tuple[int, int]:
    url = f"{LICHESS_BASE_URL}/api/games/user/{username}"
    headers = {"Accept": "application/x-chess-pgn"}

    stored = 0
    skipped = 0
    remaining = max_games
    until_ms: int | None = None
    metadata_batch: list[dict[str, object]] = []

    with tqdm(desc="Lichess games", total=max_games, unit="game") as progress:
        while True:
            page_max = batch_size
            if remaining is not None:
                page_max = min(page_max, remaining)

            params: dict[str, int] = {"max": page_max}
            if until_ms is not None:
                params["until"] = until_ms

            response = httpx.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()

            batch_count = 0
            oldest_time_ms: int | None = None
            for pgn_text, end_ms in _split_pgn_stream(response.text):
                batch_count += 1
                result = store_pgn("lichess", username, pgn_text, data_dir)
                if result is None:
                    skipped += 1
                else:
                    stored += 1
                    _path, metadata = result
                    metadata_batch.append(metadata)
                progress.update(1)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(stored + skipped, max_games or (stored + skipped))
                if end_ms is not None:
                    oldest_time_ms = (
                        end_ms
                        if oldest_time_ms is None
                        else min(oldest_time_ms, end_ms)
                    )
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        # Index all games before returning
                        index_stored_games(data_dir, metadata_batch)
                        return stored, skipped

            if batch_count == 0:
                break

            if oldest_time_ms is None:
                break
            until_ms = oldest_time_ms - 1

    # Index all games at the end
    index_stored_games(data_dir, metadata_batch)
    return stored, skipped
