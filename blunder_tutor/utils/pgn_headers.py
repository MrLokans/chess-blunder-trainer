"""PGN header extraction helpers — regex-based, no full game parse."""

from __future__ import annotations

import re

# Anchor at line start so a stray "[WhiteElo "..."]" inside a move-text comment
# (rare but possible) cannot poison the result. The header section comes first
# in any valid PGN, so the first match per side is authoritative.
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
    """Extract `(white_elo, black_elo)` from PGN headers.

    Returns `None` for missing, `?`-placeholder, empty-string, or non-numeric
    values. Trailing `?` (provisional rating annotation) is stripped before
    parsing — `"1500?"` becomes `1500`.
    """
    white = _WHITE_ELO_RE.search(pgn_content)
    black = _BLACK_ELO_RE.search(pgn_content)
    return (
        _parse_elo(white.group(1) if white else None),
        _parse_elo(black.group(1) if black else None),
    )
