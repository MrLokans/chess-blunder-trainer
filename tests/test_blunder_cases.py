"""Hand-checked blunder positions from `fixtures/blunder_cases.json`. Add a reported
misexplanation there with what must (and must not) be said about it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers.blunder_corpus import describe_blunder

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "blunder_cases.json").read_text(
        encoding="utf-8"
    )
)


def _key(message: dict[str, Any] | None) -> str | None:
    return message["key"] if message else None


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_blunder_case(case: dict[str, Any]):
    actual = describe_blunder(
        case["fen"],
        case["blunder"],
        case.get("best"),
        case.get("cp_loss", 0),
        case.get("best_line"),
        case.get("refutation_line"),
    )
    expect = case["expect"]
    produced = {
        "pattern": actual["pattern"],
        "blunder_key": _key(actual["blunder"]),
        "best_key": _key(actual["best"]),
    }

    for field, value in produced.items():
        expected = expect.get(field)
        if expected is not None:
            assert value == expected, actual
    assert expect.get("reason_contains", "") in actual["reason"], actual
    for forbidden in expect.get("forbidden_best_keys", []):
        assert _key(actual["best"]) != forbidden, actual
    for forbidden in expect.get("forbidden_blunder_keys", []):
        assert _key(actual["blunder"]) != forbidden, actual
    best_params = actual["best"]["params"] if actual["best"] else {}
    for name, value in expect.get("best_params", {}).items():
        assert best_params.get(name) == value, actual
