"""Structural enforcement of the observability facade boundary.

Convention (Phase 4 doc): service / handler / runner code calls into
``blunder_tutor.observability`` only — never imports ``sentry_sdk``
directly. The single documented exception is the ``@sentry_sdk.monitor``
decorator on the scheduler tick, which has no facade equivalent.

Mechanical enforcement is preferred over a doc-only rule (per
CLAUDE.md's self-improvement table). If this test trips, either route
the new call through the facade, or extend the allow-list with a one-line
justification for why the SDK boundary needs to be crossed at that site.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE = _ROOT / "blunder_tutor"
_IMPORT_PATTERN = re.compile(r"^\s*(?:from\s+sentry_sdk\b|import\s+sentry_sdk\b)")

# Locations authorized to import sentry_sdk directly. Add to this list
# only with a comment in the offending file justifying the exception.
# Cron monitor decorator on the scheduler has no facade equivalent —
# see the docstring on `_fanout_tick` in scheduler.py.
_ALLOWED_PATHS = frozenset(
    (
        "blunder_tutor/observability/sentry_init.py",
        "blunder_tutor/observability/scrubbing.py",
        "blunder_tutor/observability/metrics.py",
        "blunder_tutor/observability/tracing.py",
        "blunder_tutor/background/scheduler.py",
    )
)


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def test_no_unauthorized_sentry_sdk_imports() -> None:
    offenders: list[str] = []
    for path in _iter_python_files(_PACKAGE):
        rel = path.relative_to(_ROOT).as_posix()
        if rel in _ALLOWED_PATHS:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if _IMPORT_PATTERN.match(line):
                offenders.append(f"{rel}: {line.strip()}")
                break

    assert not offenders, (
        "Direct `sentry_sdk` imports found outside the observability "
        "facade. Either route the call through `blunder_tutor.observability` "
        "or add the file to `_ALLOWED_PATHS` with a comment explaining why:\n"
        + "\n".join(offenders)
    )
