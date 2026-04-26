"""Read the invite code the app already generated at startup.

``_bootstrap_auth`` in ``blunder_tutor.web.app`` writes the first-user
invite code to ``setup.invite_code`` during lifespan startup. By the
time Playwright's ``webServer`` reports the ``/health`` probe green,
this row is guaranteed to exist. Rather than pre-seeding the DB from
the test harness (which races against the app's own open handle to
``auth.sqlite3``), we open the file read-only and report the invite.

Usage::

    uv run python scripts/bootstrap_auth_db.py <auth_db_path>

Prints the invite code on success. Exits nonzero with a pointed
message if the row is missing — that means ``_bootstrap_auth`` hit
its ``log.exception`` branch, and the real diagnostic is in the
uvicorn stdout, not here.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def _read_invite(auth_db_path: Path) -> str | None:
    conn = sqlite3.connect(f"file:{auth_db_path}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT value FROM setup WHERE key = 'invite_code'"
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def main(auth_db_path: Path) -> None:
    if not auth_db_path.exists():
        print(
            f"{auth_db_path} does not exist — the app did not start "
            "or DB_PATH is misconfigured.",
            file=sys.stderr,
        )
        sys.exit(1)
    invite = _read_invite(auth_db_path)
    if not invite:
        print(
            f"{auth_db_path} has no invite_code row — check the "
            "uvicorn stdout for "
            "'Failed to generate or persist first-user invite code'.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(invite)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "usage: bootstrap_auth_db.py <auth_db_path>",
            file=sys.stderr,
        )
        sys.exit(2)
    main(Path(sys.argv[1]))
