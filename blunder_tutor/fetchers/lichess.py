from __future__ import annotations

import io
from collections.abc import Iterable

import chess.pgn
import httpx
from tqdm import tqdm

from blunder_tutor.utils.date_utils import parse_pgn_datetime_ms
from blunder_tutor.utils.pgn_utils import (
    build_game_metadata,
    compute_game_id,
    normalize_pgn,
)

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
    max_games: int | None = None,
    batch_size: int = 200,
    progress_callback: callable | None = None,
) -> tuple[list[dict[str, object]], set[str]]:
    url = f"{LICHESS_BASE_URL}/api/games/user/{username}"
    headers = {"Accept": "application/x-chess-pgn"}

    games: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    remaining = max_games
    until_ms: int | None = None

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
                normalized = normalize_pgn(pgn_text)
                game_id = compute_game_id(normalized)

                if game_id not in seen_ids:
                    metadata = build_game_metadata(pgn_text, "lichess", username)
                    if metadata:
                        games.append(metadata)
                        seen_ids.add(game_id)

                progress.update(1)

                if progress_callback:
                    progress_callback(len(games), max_games or len(games))

                if end_ms is not None:
                    oldest_time_ms = (
                        end_ms
                        if oldest_time_ms is None
                        else min(oldest_time_ms, end_ms)
                    )
                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return games, seen_ids

            if batch_count == 0:
                break

            if oldest_time_ms is None:
                break
            until_ms = oldest_time_ms - 1

    return games, seen_ids
