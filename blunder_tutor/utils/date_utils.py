from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def parse_pgn_datetime(date: str | None, time: str | None) -> datetime | None:
    if not date or not time:
        return None
    try:
        parsed = datetime.strptime(f"{date} {time}", "%Y.%m.%d %H:%M:%S")  # noqa: DTZ007 — PGN tags lack a timezone; the next line attaches UTC.
        return parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def parse_pgn_datetime_iso(date: str | None, time: str | None) -> str | None:
    dt = parse_pgn_datetime(date, time)
    return dt.isoformat() if dt else None


def parse_pgn_datetime_ms(date: str | None, time: str | None) -> int | None:
    dt = parse_pgn_datetime(date, time)
    return int(dt.timestamp() * 1000) if dt else None


def exclusive_end_bound(end_date: str) -> str:
    # end_time_utc is a full ISO timestamp, so the inclusive last day is "< next day".
    return (date.fromisoformat(end_date[:10]) + timedelta(days=1)).isoformat()
