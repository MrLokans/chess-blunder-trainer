from __future__ import annotations

from collections.abc import Callable

import httpx
from tqdm import tqdm

from blunder_tutor.utils.pgn_utils import (
    build_game_metadata,
    compute_game_id,
    normalize_pgn,
)

CHESSCOM_BASE_URL = "https://api.chess.com"


async def fetch(
    username: str,
    max_games: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[list[dict[str, object]], set[str]]:
    api_username = username.lower()
    archives_url = f"{CHESSCOM_BASE_URL}/pub/player/{api_username}/games/archives"

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(archives_url)
        response.raise_for_status()
        archives = response.json().get("archives", [])

        games: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        total_archives = len(archives)
        remaining = max_games

        with (
            tqdm(
                desc="Chess.com archives", total=total_archives, unit="archive"
            ) as archive_bar,
            tqdm(desc="Chess.com games", total=max_games, unit="game") as game_bar,
        ):
            for archive_url in reversed(archives):
                month_resp = await client.get(archive_url)
                month_resp.raise_for_status()
                archive_games = month_resp.json().get("games", [])
                for game in archive_games:
                    pgn_text = game.get("pgn")
                    if not pgn_text:
                        continue

                    normalized = normalize_pgn(pgn_text)
                    game_id = compute_game_id(normalized)

                    if game_id not in seen_ids:
                        metadata = build_game_metadata(pgn_text, "chesscom", username)
                        if metadata:
                            games.append(metadata)
                            seen_ids.add(game_id)

                    game_bar.update(1)

                    if progress_callback:
                        progress_callback(len(games), max_games or len(games))

                    if remaining is not None:
                        remaining -= 1
                        if remaining <= 0:
                            return games, seen_ids
                archive_bar.update(1)

    return games, seen_ids
