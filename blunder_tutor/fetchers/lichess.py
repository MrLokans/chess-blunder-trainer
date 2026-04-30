from __future__ import annotations

import io
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime
from http import HTTPStatus

import chess.pgn
import httpx
from tqdm import tqdm

from blunder_tutor.fetchers import USER_AGENT
from blunder_tutor.fetchers._state import FetchState
from blunder_tutor.fetchers.resilience import fetch_with_retry
from blunder_tutor.utils.date_utils import parse_pgn_datetime_ms
from blunder_tutor.utils.pgn_utils import (
    build_game_metadata,
    compute_game_id,
    normalize_pgn,
)

LICHESS_BASE_URL = "https://lichess.org"
LICHESS_USER_URL = f"{LICHESS_BASE_URL}/api/user/{{username}}"

type _FetchResult = tuple[list[dict[str, object]], set[str]]


def _split_pgn_stream(pgn_text: str) -> Iterable[tuple[str, int | None]]:
    stream = io.StringIO(pgn_text)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        buffer = io.StringIO()
        buffer.write(f"{game}\n\n")
        date = game.headers.get("UTCDate") or game.headers.get("Date")
        time = game.headers.get("UTCTime") or game.headers.get("Time")
        yield buffer.getvalue(), parse_pgn_datetime_ms(date, time)


async def fetch(
    username: str,
    max_games: int | None = None,
    since: datetime | None = None,
    batch_size: int = 200,
    progress_callback: Callable[[int, int], Awaitable[None]] | None = None,
) -> _FetchResult:
    state = FetchState(max_games=max_games, progress_callback=progress_callback)
    since_ms = int(since.timestamp() * 1000) if since is not None else None
    until_ms: int | None = None

    async with httpx.AsyncClient(timeout=60) as client:
        with tqdm(desc="Lichess games", total=max_games, unit="game") as progress:
            while True:
                batch_count, oldest_time_ms, max_reached = await _process_batch(
                    (
                        await fetch_with_retry(
                            client,
                            f"{LICHESS_BASE_URL}/api/games/user/{username}",
                            params=_lichess_params(
                                state,
                                batch_size,
                                since_ms,
                                until_ms,
                            ),
                            headers={
                                "Accept": "application/x-chess-pgn",
                                "User-Agent": USER_AGENT,
                            },
                        )
                    ).text,
                    state,
                    username,
                    progress,
                )
                if max_reached or batch_count == 0 or oldest_time_ms is None:
                    break
                until_ms = oldest_time_ms - 1

    return state.games, state.seen_ids


def _lichess_params(
    state: FetchState,
    batch_size: int,
    since_ms: int | None,
    until_ms: int | None,
) -> dict[str, int]:
    page_max = batch_size
    if state.remaining is not None:
        page_max = min(page_max, state.remaining)
    params: dict[str, int] = {"max": page_max}
    if since_ms is not None:
        params["since"] = since_ms
    if until_ms is not None:
        params["until"] = until_ms
    return params


async def _process_batch(
    response_text: str,
    state: FetchState,
    username: str,
    progress: tqdm,
) -> tuple[int, int | None, bool]:
    """Process one batch. Returns (count, oldest_time_ms, quota_exhausted)."""
    batch_count = 0
    oldest_time_ms: int | None = None
    for pgn_text, end_ms in _split_pgn_stream(response_text):
        batch_count += 1
        _try_add_game(pgn_text, username, state)
        progress.update(1)
        await state.report_progress()
        oldest_time_ms = _min_optional(oldest_time_ms, end_ms)
        if state.tick_remaining():
            return batch_count, oldest_time_ms, True
    return batch_count, oldest_time_ms, False


def _try_add_game(pgn_text: str, username: str, state: FetchState) -> None:
    game_id = compute_game_id(normalize_pgn(pgn_text))
    if game_id in state.seen_ids:
        return
    metadata = build_game_metadata(pgn_text, "lichess", username)
    if not metadata:
        return
    state.games.append(metadata)
    state.seen_ids.add(game_id)


def _min_optional(current: int | None, candidate: int | None) -> int | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return min(current, candidate)


async def validate_username(username: str) -> bool:
    url = LICHESS_USER_URL.format(username=username)
    async with httpx.AsyncClient(
        timeout=10,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        try:
            response = await client.get(url)
            return response.status_code == HTTPStatus.OK
        except httpx.HTTPError:
            return False
