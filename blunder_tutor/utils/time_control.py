from __future__ import annotations

import re
from enum import IntEnum

# Formats: "180+0", "600+5" (base+increment, seconds) and "1/86400" (correspondence).
TIME_CONTROL_WITH_INCREMENT = re.compile(r"^(\d+)\+(\d+)$")
# Chess.com often uses just seconds without increment: "600", "180"
TIME_CONTROL_SECONDS_ONLY = re.compile(r"^(\d+)$")
# Correspondence format: "1/86400" (1 move per day)
CORRESPONDENCE_PATTERN = re.compile(r"^1/(\d+)$")


class GameType(IntEnum):
    ULTRABULLET = 0
    BULLET = 1
    BLITZ = 2
    RAPID = 3
    CLASSICAL = 4
    CORRESPONDENCE = 5
    UNKNOWN = 6


GAME_TYPE_LABELS: frozendict[int, str] = frozendict(
    {
        GameType.ULTRABULLET: "ultrabullet",
        GameType.BULLET: "bullet",
        GameType.BLITZ: "blitz",
        GameType.RAPID: "rapid",
        GameType.CLASSICAL: "classical",
        GameType.CORRESPONDENCE: "correspondence",
        GameType.UNKNOWN: "unknown",
    }
)

GAME_TYPE_FROM_STRING: frozendict[str, int] = frozendict(
    {v: k for k, v in GAME_TYPE_LABELS.items()}
)

ULTRABULLET_MAX_SECONDS = 29
BULLET_MAX_SECONDS = 180  # 3 min
BLITZ_MAX_SECONDS = 480  # 8 min
RAPID_MAX_SECONDS = 1500  # 25 min

AVG_MOVES_PER_PLAYER = 40


def parse_time_control(time_control: str | None) -> tuple[int, int] | None:
    if not time_control:
        return None

    match = TIME_CONTROL_WITH_INCREMENT.match(time_control)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = TIME_CONTROL_SECONDS_ONLY.match(time_control)
    if match:
        return int(match.group(1)), 0

    return None


def estimate_game_duration(base_seconds: int, increment_seconds: int) -> int:
    return base_seconds + AVG_MOVES_PER_PLAYER * increment_seconds


_DURATION_TIERS: tuple[tuple[int, GameType], ...] = (
    (ULTRABULLET_MAX_SECONDS, GameType.ULTRABULLET),
    (BULLET_MAX_SECONDS, GameType.BULLET),
    (BLITZ_MAX_SECONDS, GameType.BLITZ),
    (RAPID_MAX_SECONDS, GameType.RAPID),
)


def _duration_to_game_type(duration: int) -> GameType:
    for threshold, game_type in _DURATION_TIERS:
        if duration < threshold:
            return game_type
    return GameType.CLASSICAL


def classify_game_type(time_control: str | None) -> GameType:
    if not time_control:
        return GameType.UNKNOWN

    # Chess.com uses "-" for daily/correspondence games
    if time_control == "-":
        return GameType.CORRESPONDENCE

    if CORRESPONDENCE_PATTERN.match(time_control):
        return GameType.CORRESPONDENCE

    parsed = parse_time_control(time_control)
    if not parsed:
        return GameType.UNKNOWN

    base, increment = parsed
    return _duration_to_game_type(estimate_game_duration(base, increment))


def get_game_type_label(game_type: GameType | int) -> str:
    return GAME_TYPE_LABELS.get(int(game_type), "unknown")
