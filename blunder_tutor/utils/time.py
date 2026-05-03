from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return utcnow().isoformat()


def parse_dt(raw: str) -> datetime:
    """Parse a stored timestamp into a tz-aware datetime.

    Naive ISO inputs (legacy: pre-migration writes used
    ``datetime.utcnow().isoformat()``) are coerced to UTC so callers can
    rely on aware datetimes for arithmetic and comparison without
    ``TypeError`` on naive/aware mixing.
    """
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
