from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from blunder_tutor.utils.time import now_iso, parse_dt, utcnow


class TestNowIso:
    def test_returns_aware_iso_with_utc_offset(self):
        value = now_iso()
        assert value.endswith("+00:00"), value

    def test_round_trips_through_parse_dt(self):
        before = utcnow()
        parsed = parse_dt(now_iso())
        after = utcnow()
        assert before <= parsed <= after
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)


class TestUtcnow:
    def test_returns_aware_utc_datetime(self):
        value = utcnow()
        assert value.tzinfo is not None
        assert value.utcoffset() == timedelta(0)

    def test_value_is_recent(self):
        before = datetime.now(UTC)
        value = utcnow()
        after = datetime.now(UTC)
        assert before <= value <= after


class TestParseDt:
    def test_aware_utc_input_returns_aware_utc(self):
        raw = "2026-05-03T12:34:56.789012+00:00"
        parsed = parse_dt(raw)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)
        assert parsed.year == 2026
        assert parsed.microsecond == 789012

    def test_naive_input_is_coerced_to_utc(self):
        # Legacy bridge: pre-migration writes used `datetime.utcnow().isoformat()`
        # and produced naive ISO strings. After migration, parse_dt must keep
        # interpreting them as UTC so existing rows in user DBs stay readable.
        raw = "2026-05-03T12:34:56.789012"
        parsed = parse_dt(raw)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)

    def test_non_utc_offset_is_preserved(self):
        raw = "2026-05-03T14:34:56+02:00"
        parsed = parse_dt(raw)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(hours=2)

    def test_mixed_legacy_and_new_can_be_subtracted(self):
        # The whole point of routing reads through parse_dt: a column may
        # contain naive (legacy) and aware (post-migration) ISO strings, and
        # arithmetic between them must not raise TypeError.
        legacy = parse_dt("2026-05-03T12:00:00")
        new = parse_dt("2026-05-03T12:00:30+00:00")
        delta = new - legacy
        assert delta == timedelta(seconds=30)

    @pytest.mark.parametrize("bad", ["", "not-a-date", "2026-13-99T00:00:00"])
    def test_invalid_input_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            parse_dt(bad)
