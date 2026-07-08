from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from blunder_tutor.srs import (
    LADDER_DAYS,
    LEECH_FAILURE_THRESHOLD,
    CardState,
    SrsCard,
    enroll,
    transition,
)

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


def make_card(**overrides: object) -> SrsCard:
    base: dict[str, object] = {
        "game_id": "g1",
        "ply": 10,
        "rung": 0,
        "state": CardState.ACTIVE,
        "due_at": NOW.isoformat(),
        "enrolled_at": NOW.isoformat(),
        "last_reviewed_at": None,
        "total_failures": 1,
    }
    base.update(overrides)
    return SrsCard(**base)  # type: ignore[arg-type]


class TestEnroll:
    def test_enrolls_at_rung_zero_due_tomorrow(self):
        card = enroll("g1", 10, NOW)
        assert card.rung == 0
        assert card.state is CardState.ACTIVE
        assert card.due_at == (NOW + timedelta(days=1)).isoformat()
        assert card.total_failures == 1


class TestTransition:
    @pytest.mark.parametrize("rung", range(len(LADDER_DAYS) - 1))
    def test_pass_climbs_one_rung(self, rung: int):
        card = transition(make_card(rung=rung), passed=True, now=NOW)
        assert card.rung == rung + 1
        assert card.state is CardState.ACTIVE
        expected_due = (NOW + timedelta(days=LADDER_DAYS[rung + 1])).isoformat()
        assert card.due_at == expected_due
        assert card.last_reviewed_at == NOW.isoformat()

    def test_pass_on_top_rung_graduates(self):
        card = transition(make_card(rung=len(LADDER_DAYS) - 1), passed=True, now=NOW)
        assert card.state is CardState.GRADUATED

    @pytest.mark.parametrize("rung", [1, 3, 4])
    def test_fail_resets_to_rung_zero_due_tomorrow(self, rung: int):
        card = transition(make_card(rung=rung), passed=False, now=NOW)
        assert card.rung == 0
        assert card.state is CardState.ACTIVE
        assert card.due_at == (NOW + timedelta(days=1)).isoformat()
        assert card.total_failures == 2

    def test_fail_at_threshold_suspends_as_leech(self):
        card = transition(
            make_card(total_failures=LEECH_FAILURE_THRESHOLD - 1),
            passed=False,
            now=NOW,
        )
        assert card.state is CardState.SUSPENDED
        assert card.total_failures == LEECH_FAILURE_THRESHOLD

    def test_transition_does_not_mutate_input(self):
        original = make_card()
        transition(original, passed=True, now=NOW)
        assert original.rung == 0
