"""Time control parsing and game type classification utilities."""

from __future__ import annotations

import re
from enum import IntEnum

# Time control patterns
# Format: "base+increment" where base is seconds and increment is seconds
# Examples: "180+0" (3 min), "600+5" (10 min + 5 sec), "1/86400" (correspondence)
TIME_CONTROL_PATTERN = re.compile(r"^(\d+)\+(\d+)$")
CORRESPONDENCE_PATTERN = re.compile(r"^1/(\d+)$")


class GameType(IntEnum):
    ULTRABULLET = 0
    BULLET = 1
    BLITZ = 2
    RAPID = 3
    CLASSICAL = 4
    CORRESPONDENCE = 5
    UNKNOWN = 6


GAME_TYPE_LABELS: dict[int, str] = {
    GameType.ULTRABULLET: "ultrabullet",
    GameType.BULLET: "bullet",
    GameType.BLITZ: "blitz",
    GameType.RAPID: "rapid",
    GameType.CLASSICAL: "classical",
    GameType.CORRESPONDENCE: "correspondence",
    GameType.UNKNOWN: "unknown",
}

GAME_TYPE_FROM_STRING: dict[str, int] = {v: k for k, v in GAME_TYPE_LABELS.items()}


def parse_time_control(time_control: str | None) -> tuple[int, int] | None:
    """Parse time control string into (base_seconds, increment_seconds).

    Returns None if the format is not recognized.
    """
    if not time_control:
        return None

    match = TIME_CONTROL_PATTERN.match(time_control)
    if match:
        return int(match.group(1)), int(match.group(2))

    return None


def estimate_game_duration(base_seconds: int, increment_seconds: int) -> int:
    """Estimate total game duration in seconds.

    Uses the standard formula: base + 40 * increment
    (assuming ~40 moves per player in a typical game)
    """
    return base_seconds + 40 * increment_seconds


def classify_game_type(time_control: str | None) -> GameType:
    """Classify a game into a type based on its time control.

    Classification follows Lichess standards:
    - UltraBullet: estimated duration < 29 seconds
    - Bullet: estimated duration < 180 seconds (3 minutes)
    - Blitz: estimated duration < 480 seconds (8 minutes)
    - Rapid: estimated duration < 1500 seconds (25 minutes)
    - Classical: estimated duration >= 1500 seconds
    - Correspondence: daily/multi-day games
    """
    if not time_control:
        return GameType.UNKNOWN

    # Check for correspondence format
    if CORRESPONDENCE_PATTERN.match(time_control):
        return GameType.CORRESPONDENCE

    parsed = parse_time_control(time_control)
    if not parsed:
        return GameType.UNKNOWN

    base, increment = parsed
    duration = estimate_game_duration(base, increment)

    if duration < 29:
        return GameType.ULTRABULLET
    if duration < 180:
        return GameType.BULLET
    if duration < 480:
        return GameType.BLITZ
    if duration < 1500:
        return GameType.RAPID
    return GameType.CLASSICAL


def get_game_type_label(game_type: GameType | int) -> str:
    """Get human-readable label for a game type."""
    return GAME_TYPE_LABELS.get(int(game_type), "unknown")


def get_game_type_from_label(label: str) -> GameType:
    """Get GameType from its string label."""
    return GameType(GAME_TYPE_FROM_STRING.get(label.lower(), GameType.UNKNOWN))
