from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return utcnow().isoformat()


def parse_dt(raw: str) -> datetime:
    """Naive ISO inputs (legacy `datetime.utcnow().isoformat()` writes) are coerced to UTC
    so callers can compare aware datetimes safely."""
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
