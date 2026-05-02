from __future__ import annotations

from blunder_tutor.repositories.profile_types import ProfileStatSnapshot

# Canonical mode set for v1. All other platform-specific modes are dropped
# (Lichess variants, Chess.com tactics/lessons, etc.). Order is the
# rendering order used by tests and downstream UI.
CANONICAL_MODES: tuple[str, ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
    "correspondence",
)

# Chess.com keys its stats blocks with a `chess_` prefix and uses `daily`
# where we use `correspondence`.
_CHESSCOM_KEY_TO_CANONICAL: tuple[tuple[str, str], ...] = (
    ("chess_bullet", "bullet"),
    ("chess_blitz", "blitz"),
    ("chess_rapid", "rapid"),
    ("chess_daily", "correspondence"),
)


def lichess_to_canonical(perfs: dict[str, object]) -> list[ProfileStatSnapshot]:
    """Map a Lichess `/api/user/{username}` `perfs` block to canonical snapshots.

    Drops non-canonical modes (puzzle, racingKings, crazyhouse, chess960,
    kingOfTheHill, threeCheck, antichess, atomic, horde, ultraBullet, ...)
    by iterating only over `CANONICAL_MODES`.
    """
    snapshots: list[ProfileStatSnapshot] = []
    for mode in CANONICAL_MODES:
        perf = perfs.get(mode)
        if not isinstance(perf, dict):
            continue
        snapshots.append(
            ProfileStatSnapshot(
                mode=mode,
                rating=_int_or_none(perf.get("rating")),
                games_count=_int_or_zero(perf.get("games")),
            )
        )
    return snapshots


def chesscom_to_canonical(stats: dict[str, object]) -> list[ProfileStatSnapshot]:
    """Map a Chess.com `/pub/player/{u}/stats` payload to canonical snapshots.

    Sums `record.{win,loss,draw}` for `games_count`. Maps `chess_daily` →
    `correspondence`. Drops `tactics`, `lessons`, `puzzle_rush`, and any
    variant-specific blocks (e.g. `chess960_daily`).
    """
    snapshots: list[ProfileStatSnapshot] = []
    for cc_key, canonical in _CHESSCOM_KEY_TO_CANONICAL:
        block = stats.get(cc_key)
        if not isinstance(block, dict):
            continue
        last = block.get("last") if isinstance(block.get("last"), dict) else {}
        record = block.get("record") if isinstance(block.get("record"), dict) else {}
        snapshots.append(
            ProfileStatSnapshot(
                mode=canonical,
                rating=_int_or_none(last.get("rating")),
                games_count=(
                    _int_or_zero(record.get("win"))
                    + _int_or_zero(record.get("loss"))
                    + _int_or_zero(record.get("draw"))
                ),
            )
        )
    return snapshots


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _int_or_zero(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
