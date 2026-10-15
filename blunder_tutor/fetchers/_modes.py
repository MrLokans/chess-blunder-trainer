from __future__ import annotations

from blunder_tutor.repositories.profile_types import ProfileStatSnapshot

# Canonical v1 set; order is the rendering order.
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
    """`chess_daily` maps to `correspondence`; other blocks are dropped."""
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
