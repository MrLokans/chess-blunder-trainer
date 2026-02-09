from __future__ import annotations

import hashlib
import io
import time
from typing import Any

import chess.pgn
from fastapi.routing import APIRouter
from pydantic import BaseModel

from blunder_tutor.events import JobExecutionRequestEvent
from blunder_tutor.web.dependencies import (
    ConfigDep,
    EventBusDep,
    GameRepoDep,
    JobServiceDep,
    SettingsRepoDep,
)

import_router = APIRouter()


class ImportRequest(BaseModel):
    pgn: str


class ImportResponse(BaseModel):
    success: bool
    job_id: str | None = None
    game_id: str | None = None
    errors: list[str] | None = None


def _validate_and_parse_pgn(pgn_text: str) -> tuple[chess.pgn.Game | None, list[str]]:
    pgn_text = pgn_text.strip()
    if not pgn_text:
        return None, ["Invalid PGN format"]

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text), Visitor=chess.pgn.GameBuilder)
    except Exception:
        return None, ["Invalid PGN format"]

    if game is None:
        return None, ["Invalid PGN format"]

    if game.errors:
        return None, [f"Illegal move in PGN: {e}" for e in game.errors[:3]]

    if not list(game.mainline_moves()):
        return None, ["PGN contains no moves"]

    return game, []


def _normalize_pgn_date(pgn_date: str) -> str | None:
    """Convert PGN date like '2024.01.15' to ISO '2024-01-15', or None if invalid."""
    if not pgn_date or "?" in pgn_date:
        return None
    return pgn_date.replace(".", "-")


def _generate_game_id(pgn_text: str) -> str:
    ts = int(time.time())
    h = hashlib.sha256(pgn_text.encode()).hexdigest()[:8]
    return f"manual-{ts}-{h}"


def _build_game_dict(
    game_id: str,
    game: chess.pgn.Game,
    pgn_text: str,
    username: str,
) -> dict[str, object]:
    headers = game.headers
    return {
        "id": game_id,
        "source": "manual-import",
        "username": username,
        "white": headers.get("White", "?"),
        "black": headers.get("Black", "?"),
        "result": headers.get("Result", "*"),
        "date": _normalize_pgn_date(headers.get("Date", "")),
        "end_time_utc": _normalize_pgn_date(headers.get("Date", "")),
        "time_control": headers.get("TimeControl", ""),
        "pgn_content": pgn_text,
    }


@import_router.post("/api/import/pgn", response_model=ImportResponse)
async def import_pgn(
    payload: ImportRequest,
    config: ConfigDep,
    settings_repo: SettingsRepoDep,
    game_repo: GameRepoDep,
    job_service: JobServiceDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    game, errors = _validate_and_parse_pgn(payload.pgn)
    if errors:
        return {"success": False, "errors": errors}

    assert game is not None

    username = config.username
    if not username:
        usernames = await settings_repo.get_configured_usernames()
        username = next(iter(usernames.values())) if usernames else "anonymous"

    game_id = _generate_game_id(payload.pgn)

    existing = await game_repo.get_game(game_id)
    if existing:
        return {"success": False, "errors": ["Game already imported"]}

    game_dict = _build_game_dict(game_id, game, payload.pgn.strip(), username)
    await game_repo.insert_games([game_dict])

    job_id = await job_service.create_job(
        job_type="import_pgn",
        username=username,
        max_games=1,
    )

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="import_pgn",
        game_id=game_id,
        username=username,
    )
    await event_bus.publish(event)

    return {"success": True, "job_id": job_id, "game_id": game_id}
