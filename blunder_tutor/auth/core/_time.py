from __future__ import annotations

from datetime import UTC, datetime


def parse_dt(raw: str) -> datetime:
    """Parse a stored timestamp into a tz-aware UTC datetime.

    All writes go through :func:`now_iso` and use
    ``datetime.now(UTC).isoformat()``, yielding ISO-8601 with explicit
    ``+00:00``. The fallback to ``UTC`` for naive input exists only for
    legacy rows (none in production yet).
    """
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
