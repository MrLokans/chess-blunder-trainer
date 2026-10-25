"""Every demo-DB blunder through the tactics detector and the explanation generator,
compared against a committed snapshot. Intentional changes: rerun with UPDATE_SNAPSHOTS=1
and review the snapshot diff."""

from __future__ import annotations

import difflib
import os
from pathlib import Path

import pytest

from tests.helpers.blunder_corpus import DEMO_DB, format_record, iter_db_blunders

SNAPSHOT = Path(__file__).parent / "fixtures" / "snapshots" / "demo_blunders.txt"
MAX_DIFF_LINES = 40


@pytest.mark.skipif(not DEMO_DB.exists(), reason="demo DB not available")
def test_demo_blunders_match_snapshot():
    actual = [format_record(record) for record in iter_db_blunders(DEMO_DB)]

    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text("\n".join(actual) + "\n", encoding="utf-8")
        return

    if not SNAPSHOT.exists():
        pytest.fail(
            f"{SNAPSHOT} is missing; create it with UPDATE_SNAPSHOTS=1", pytrace=False
        )
    expected = SNAPSHOT.read_text(encoding="utf-8").splitlines()
    if actual == expected:
        return
    diff = list(difflib.unified_diff(expected, actual, "snapshot", "current", n=0))
    changed = sum(1 for line in diff if line.startswith("+") and line[1:2] != "+")
    pytest.fail(
        f"{changed} of {len(actual)} demo blunders changed; if intended, rerun with "
        f"UPDATE_SNAPSHOTS=1 and review the diff of {SNAPSHOT.name}.\n"
        + "\n".join(diff[:MAX_DIFF_LINES]),
        pytrace=False,
    )
