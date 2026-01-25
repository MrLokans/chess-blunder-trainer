from __future__ import annotations

from datetime import UTC, datetime


def parse_pgn_datetime(date: str | None, time: str | None) -> datetime | None:
    if not date or not time:
        return None
    try:
        parsed = datetime.strptime(f"{date} {time}", "%Y.%m.%d %H:%M:%S")
        return parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def parse_pgn_datetime_iso(date: str | None, time: str | None) -> str | None:
    dt = parse_pgn_datetime(date, time)
    return dt.isoformat() if dt else None


def parse_pgn_datetime_ms(date: str | None, time: str | None) -> int | None:
    dt = parse_pgn_datetime(date, time)
    return int(dt.timestamp() * 1000) if dt else None
