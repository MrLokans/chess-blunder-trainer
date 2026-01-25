from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blunder_tutor.utils.date_utils import (
    parse_pgn_datetime,
    parse_pgn_datetime_iso,
    parse_pgn_datetime_ms,
)


class TestParsePgnDatetime:
    def test_valid_datetime(self):
        date = "2023.12.25"
        time = "14:30:45"
        result = parse_pgn_datetime(date, time)
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo == UTC

    def test_none_date(self):
        assert parse_pgn_datetime(None, "14:30:45") is None

    def test_none_time(self):
        assert parse_pgn_datetime("2023.12.25", None) is None

    def test_both_none(self):
        assert parse_pgn_datetime(None, None) is None

    def test_invalid_date_format(self):
        assert parse_pgn_datetime("2023-12-25", "14:30:45") is None
        assert parse_pgn_datetime("25.12.2023", "14:30:45") is None

    def test_invalid_time_format(self):
        assert parse_pgn_datetime("2023.12.25", "14-30-45") is None
        assert parse_pgn_datetime("2023.12.25", "2:30:45 PM") is None

    def test_empty_strings(self):
        assert parse_pgn_datetime("", "14:30:45") is None
        assert parse_pgn_datetime("2023.12.25", "") is None


class TestParsePgnDatetimeIso:
    def test_valid_datetime(self):
        date = "2023.12.25"
        time = "14:30:45"
        result = parse_pgn_datetime_iso(date, time)
        assert result is not None
        assert "2023-12-25T14:30:45" in result
        assert "+00:00" in result or result.endswith("Z")

    def test_none_returns_none(self):
        assert parse_pgn_datetime_iso(None, "14:30:45") is None
        assert parse_pgn_datetime_iso("2023.12.25", None) is None

    def test_invalid_datetime(self):
        assert parse_pgn_datetime_iso("invalid", "14:30:45") is None


class TestParsePgnDatetimeMs:
    def test_valid_datetime(self):
        date = "2023.12.25"
        time = "14:30:45"
        result = parse_pgn_datetime_ms(date, time)
        assert result is not None
        assert isinstance(result, int)
        assert result > 0
        # Verify it's a reasonable timestamp (after year 2000)
        assert result > 946684800000  # 2000-01-01 in ms

    def test_none_returns_none(self):
        assert parse_pgn_datetime_ms(None, "14:30:45") is None
        assert parse_pgn_datetime_ms("2023.12.25", None) is None

    def test_invalid_datetime(self):
        assert parse_pgn_datetime_ms("invalid", "14:30:45") is None

    def test_known_timestamp(self):
        # 2024-01-01 00:00:00 UTC = 1704067200000 ms
        date = "2024.01.01"
        time = "00:00:00"
        result = parse_pgn_datetime_ms(date, time)
        assert result == 1704067200000
