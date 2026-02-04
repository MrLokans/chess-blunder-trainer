from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import datetime

import httpx
from tqdm import tqdm

from blunder_tutor.fetchers import USER_AGENT
from blunder_tutor.fetchers.resilience import fetch_with_retry
from blunder_tutor.utils.pgn_utils import (
    build_game_metadata,
    compute_game_id,
    normalize_pgn,
)

CHESSCOM_BASE_URL = "https://api.chess.com"
ARCHIVE_URL_PATTERN = re.compile(r"/games/(\d{4})/(\d{2})$")


def _parse_archive_month(archive_url: str) -> tuple[int, int] | None:
    """Extract (year, month) from archive URL like '.../games/2024/01'."""
    match = ARCHIVE_URL_PATTERN.search(archive_url)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _filter_archives_since(archives: list[str], since: datetime | None) -> list[str]:
    """Filter archives to only include those that may contain games after `since`."""
    if since is None:
        return archives

    since_year, since_month = since.year, since.month
    filtered = []
    for url in archives:
        parsed = _parse_archive_month(url)
        if parsed is None:
            filtered.append(url)
            continue
        year, month = parsed
        if (year, month) >= (since_year, since_month):
            filtered.append(url)
    return filtered


async def fetch(
    username: str,
    max_games: int | None = None,
    since: datetime | None = None,
    progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
) -> tuple[list[dict[str, object]], set[str]]:
    api_username = username.lower()
    archives_url = f"{CHESSCOM_BASE_URL}/pub/player/{api_username}/games/archives"

    headers = {"User-Agent": USER_AGENT}

    since_ts: int | None = None
    if since is not None:
        since_ts = int(since.timestamp())

    async with httpx.AsyncClient(
        timeout=60, follow_redirects=True, headers=headers
    ) as client:
        response = await fetch_with_retry(client, archives_url)
        all_archives = response.json().get("archives", [])
        archives = _filter_archives_since(all_archives, since)

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
                month_resp = await fetch_with_retry(client, archive_url)
                archive_games = month_resp.json().get("games", [])
                for game in reversed(archive_games):
                    # Filter by timestamp if since is specified
                    if since_ts is not None:
                        end_time = game.get("end_time", 0)
                        if end_time < since_ts:
                            continue

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
                        await progress_callback(len(games), max_games or len(games))

                    if remaining is not None:
                        remaining -= 1
                        if remaining <= 0:
                            return games, seen_ids
                archive_bar.update(1)

    return games, seen_ids
