"""Structural guard for ``app.state.none_mode_db_path`` (TREK-22).

The attribute is set ONLY in ``AUTH_MODE=none`` (see
``blunder_tutor.web.app.create_app``). Reading it from any code path
that can execute under ``AUTH_MODE=credentials`` raises AttributeError
— but only at the moment that code path is exercised. This test
catches the bug at edit time by greping the source tree and asserting
that only documented call sites reference the attribute.

Add a new reader: update :data:`ALLOWED_READERS`. Don't introduce a
reader without first verifying the surrounding control flow guarantees
none-mode (e.g., gated on ``service is None`` or ``mode == "none"``).

The legacy spelling ``app.state.legacy_db_path`` is also forbidden so
a stray re-introduction of the old attribute name fails CI.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "blunder_tutor"

# Modules permitted to read or write ``app.state.none_mode_db_path``.
# Paths are repo-relative POSIX strings.
ALLOWED_READERS = frozenset(
    (
        # sole writer; per-user DB path now routes through
        # `app.state.db_path_resolver` + `UserDbPathMiddleware` instead
        # of being read directly from `none_mode_db_path` by other modules.
        # Lives in app_lifecycle.py (split from app.py to keep the latter
        # a thin builder); the writer is gated on `mode == AUTH_MODE_NONE`
        # in `_init_state`.
        "blunder_tutor/web/app_lifecycle.py",
    )
)


_NONE_MODE_PATTERN = re.compile(r"app\.state\.none_mode_db_path\b")
_LEGACY_PATTERN = re.compile(r"app\.state\.legacy_db_path\b")


def _files_matching(pattern: re.Pattern[str]) -> set[str]:
    hits: set[str] = set()
    for path in SOURCE_ROOT.rglob("*.py"):
        text = path.read_text()
        if pattern.search(text):
            hits.add(path.relative_to(REPO_ROOT).as_posix())
    return hits


class TestNoneModeDbPathIsolation:
    def test_none_mode_db_path_only_in_allowlist(self):
        actual = _files_matching(_NONE_MODE_PATTERN)
        unexpected = actual - ALLOWED_READERS
        assert unexpected == set(), (
            f"Unexpected access to app.state.none_mode_db_path in {sorted(unexpected)}. "
            "If this read is genuinely none-mode-only, add the file to "
            "tests/test_none_mode_db_path_isolation.py::ALLOWED_READERS with "
            "a comment naming the gate. Otherwise route through "
            "request.state.user_db_path / the get_db_path dependency."
        )

    def test_legacy_db_path_name_is_extinct(self):
        hits = _files_matching(_LEGACY_PATTERN)
        assert hits == set(), (
            f"`app.state.legacy_db_path` was renamed to `none_mode_db_path` in "
            f"TREK-22. Update {sorted(hits)} to use the new name."
        )
