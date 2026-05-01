from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from http import HTTPStatus

import httpx
from tqdm import tqdm

from blunder_tutor.fetchers import USER_AGENT, ExistenceCheck, RateLimitError
from blunder_tutor.fetchers._modes import chesscom_to_canonical
from blunder_tutor.fetchers._state import FetchState
from blunder_tutor.fetchers.resilience import RetryableHTTPError, fetch_with_retry
from blunder_tutor.repositories.profile_types import ProfileStatSnapshot
from blunder_tutor.utils.pgn_utils import (
    build_game_metadata,
    compute_game_id,
    normalize_pgn,
)

CHESSCOM_BASE_URL = "https://api.chess.com"
CHESSCOM_USER_URL = f"{CHESSCOM_BASE_URL}/pub/player/{{username}}"
CHESSCOM_STATS_URL = f"{CHESSCOM_BASE_URL}/pub/player/{{username}}/stats"
_USER_AGENT_HEADER_KEY = "User-Agent"
ARCHIVE_URL_PATTERN = re.compile(r"/games/(\d{4})/(\d{2})$")

type _FetchResult = tuple[list[dict[str, object]], set[str]]


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
) -> _FetchResult:
    state = FetchState(max_games=max_games, progress_callback=progress_callback)
    since_ts = int(since.timestamp()) if since is not None else None

    async with httpx.AsyncClient(
        timeout=60,
        follow_redirects=True,
        headers={_USER_AGENT_HEADER_KEY: USER_AGENT},
    ) as client:
        archives = _filter_archives_since(
            (
                await fetch_with_retry(
                    client,
                    f"{CHESSCOM_BASE_URL}/pub/player/{username.lower()}/games/archives",
                )
            )
            .json()
            .get("archives", []),
            since,
        )

        with (
            tqdm(
                desc="Chess.com archives",
                total=len(archives),
                unit="archive",
            ) as archive_bar,
            tqdm(desc="Chess.com games", total=max_games, unit="game") as game_bar,
        ):
            for archive_url in reversed(archives):
                archive_games = (
                    (await fetch_with_retry(client, archive_url))
                    .json()
                    .get("games", [])
                )
                if await _process_archive(
                    archive_games,
                    state,
                    since_ts,
                    username,
                    game_bar,
                ):
                    break
                archive_bar.update(1)

    return state.games, state.seen_ids


async def _process_archive(
    archive_games: list[dict[str, object]],
    state: FetchState,
    since_ts: int | None,
    username: str,
    game_bar: tqdm,
) -> bool:
    """Process one archive's games. Returns True iff the quota was exhausted."""
    for raw_game in reversed(archive_games):
        if not _passes_initial_filter(raw_game, since_ts):
            continue
        _try_add_game(raw_game, username, state)
        game_bar.update(1)
        await state.report_progress()
        if state.tick_remaining():
            return True
    return False


def _passes_initial_filter(
    raw_game: dict[str, object],
    since_ts: int | None,
) -> bool:
    if since_ts is not None and (raw_game.get("end_time") or 0) < since_ts:
        return False
    return bool(raw_game.get("pgn"))


def _try_add_game(
    raw_game: dict[str, object],
    username: str,
    state: FetchState,
) -> None:
    pgn_text = raw_game["pgn"]
    game_id = compute_game_id(normalize_pgn(pgn_text))
    if game_id in state.seen_ids:
        return
    metadata = build_game_metadata(pgn_text, "chesscom", username)
    if not metadata:
        return
    state.games.append(metadata)
    state.seen_ids.add(game_id)


async def validate_username(username: str) -> bool:
    url = CHESSCOM_USER_URL.format(username=username.lower())
    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={_USER_AGENT_HEADER_KEY: USER_AGENT},
    ) as client:
        try:
            response = await client.get(url)
            return response.status_code == HTTPStatus.OK
        except httpx.HTTPError:
            return False


async def fetch_user_stats(username: str) -> list[ProfileStatSnapshot]:
    """Fetch per-mode rating + game count from Chess.com `/pub/player/{u}/stats`.

    Raises `RateLimitError` if Chess.com persistently 429s the request after
    the resilience layer's retry budget is exhausted. 404s and other
    non-retryable status codes propagate as `httpx.HTTPStatusError`.
    """
    url = CHESSCOM_STATS_URL.format(username=username.lower())
    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={_USER_AGENT_HEADER_KEY: USER_AGENT},
    ) as client:
        try:
            response = await fetch_with_retry(client, url)
        except RetryableHTTPError as exc:
            if exc.response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                raise RateLimitError("chesscom") from exc
            raise
    payload = response.json()
    if not isinstance(payload, dict):
        return []
    return chesscom_to_canonical(payload)


async def check_username_existence(username: str) -> ExistenceCheck:
    """Check whether a Chess.com user exists, with rate-limit awareness.

    Distinguishes 404 (`exists=False`) from persistent 429
    (`rate_limited=True`). 5xx and other non-retryable errors propagate.
    """
    url = CHESSCOM_USER_URL.format(username=username.lower())
    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={_USER_AGENT_HEADER_KEY: USER_AGENT},
    ) as client:
        try:
            await fetch_with_retry(client, url)
        except RetryableHTTPError as exc:
            if exc.response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                return ExistenceCheck(exists=False, rate_limited=True)
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == HTTPStatus.NOT_FOUND:
                return ExistenceCheck(exists=False, rate_limited=False)
            raise
    return ExistenceCheck(exists=True, rate_limited=False)
