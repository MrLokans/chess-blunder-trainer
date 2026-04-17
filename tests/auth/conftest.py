from __future__ import annotations

from pathlib import Path

import pytest

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.schema import initialize_auth_schema


@pytest.fixture
async def auth_db(tmp_path: Path) -> AuthDb:
    """Return a connected :class:`AuthDb` against a fresh, migrated
    ``auth.sqlite3`` in the test's temp dir."""
    path = tmp_path / "auth.sqlite3"
    await initialize_auth_schema(path)
    db = AuthDb(path)
    await db.connect()
    yield db
    await db.close()
