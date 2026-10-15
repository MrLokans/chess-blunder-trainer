from __future__ import annotations

import re

# Anchored at line start so a `[WhiteElo ...]` inside a move comment can't poison the
# result; the first match per side wins.
_WHITE_ELO_RE = re.compile(r'^\[WhiteElo "([^"]*)"\]', re.MULTILINE)
_BLACK_ELO_RE = re.compile(r'^\[BlackElo "([^"]*)"\]', re.MULTILINE)
# Trailing-"?" tolerated for provisional ratings ("1500?").
_LEADING_INT_RE = re.compile(r"^(\d+)")


def _parse_elo(raw: str | None) -> int | None:
    if raw is None:
        return None
    match = _LEADING_INT_RE.match(raw)
    return int(match.group(1)) if match else None


def extract_player_elos(pgn_content: str) -> tuple[int | None, int | None]:
    """`None` for missing, `?`, empty or non-numeric values; a trailing `?` (provisional
    rating) is stripped."""
    white = _WHITE_ELO_RE.search(pgn_content)
    black = _BLACK_ELO_RE.search(pgn_content)
    return (
        _parse_elo(white.group(1) if white else None),
        _parse_elo(black.group(1) if black else None),
    )
