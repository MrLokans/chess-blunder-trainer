from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.profile_types import (
    ProfileNotFoundError,
    ProfileRepository,
)
from blunder_tutor.utils.pgn_headers import extract_player_elos
from blunder_tutor.utils.time import utcnow
from blunder_tutor.utils.time_control import (
    GAME_TYPE_FROM_STRING,
    GameType,
    get_game_type_label,
)

_WINDOW_DAYS = 30

Color = Literal["white", "black"]


@dataclass(frozen=True, slots=True)
class RatingPoint:
    end_time_utc: str
    rating: int
    game_type: str
    color: Color
    opponent_rating: int | None


def _resolve_mode(mode: str | None) -> int | None:
    if mode is None:
        return None
    label = mode.lower()
    if label not in GAME_TYPE_FROM_STRING:
        raise ValueError(f"unknown mode: {mode}")
    resolved = GAME_TYPE_FROM_STRING[label]
    # `unknown` is a sentinel for un-classified rows, not a user-facing mode.
    if resolved == GameType.UNKNOWN:
        raise ValueError(f"unknown mode: {mode}")
    return int(resolved)


def _pick_side(
    *,
    profile_username: str,
    white: str | None,
    black: str | None,
    white_elo: int | None,
    black_elo: int | None,
) -> tuple[Color, int, int | None] | None:
    """Return `(color, rating, opponent_rating)` for the side matching the
    profile's username, or `None` if neither side matches or that side's Elo
    is missing.
    """
    target = profile_username.lower()
    if white and white.lower() == target:
        if white_elo is None:
            return None
        return "white", white_elo, black_elo
    if black and black.lower() == target:
        if black_elo is None:
            return None
        return "black", black_elo, white_elo
    return None


def _row_to_point(
    row: dict[str, object], *, profile_username: str
) -> RatingPoint | None:
    white_elo, black_elo = extract_player_elos(str(row["pgn_content"]))
    picked = _pick_side(
        profile_username=profile_username,
        white=row.get("white"),  # type: ignore[arg-type]
        black=row.get("black"),  # type: ignore[arg-type]
        white_elo=white_elo,
        black_elo=black_elo,
    )
    if picked is None:
        return None
    color, rating, opponent_rating = picked
    return RatingPoint(
        end_time_utc=str(row["end_time_utc"]),
        rating=rating,
        game_type=get_game_type_label(int(row["game_type"])),
        color=color,
        opponent_rating=opponent_rating,
    )


class RatingHistoryService:
    def __init__(
        self,
        *,
        profiles: ProfileRepository,
        games: GameRepository,
    ) -> None:
        self._profiles = profiles
        self._games = games

    async def get(
        self,
        profile_id: int,
        *,
        mode: str | None = None,
    ) -> list[RatingPoint]:
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"profile not found: {profile_id}")

        cutoff = (utcnow() - timedelta(days=_WINDOW_DAYS)).isoformat()
        rows = await self._games.list_rating_history_rows(
            profile_id, game_type=_resolve_mode(mode), since=cutoff
        )
        return [
            point
            for row in rows
            if (point := _row_to_point(row, profile_username=profile.username))
            is not None
        ]
