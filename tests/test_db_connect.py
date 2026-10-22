from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite
import pytest

from blunder_tutor.analysis.db import _connect_async
from blunder_tutor.repositories import base


async def test_interrupted_setup_closes_connection(tmp_path: Path, monkeypatch):
    opened: list[aiosqlite.Connection] = []
    real_execute = aiosqlite.Connection.execute

    def cancelled_execute(self, *args, **kwargs):
        opened.append(self)
        monkeypatch.setattr(aiosqlite.Connection, "execute", real_execute)
        raise asyncio.CancelledError

    monkeypatch.setattr(aiosqlite.Connection, "execute", cancelled_execute)

    with pytest.raises(asyncio.CancelledError):
        await _connect_async(tmp_path / "db.sqlite3")

    leaked = opened[0]._connection is not None
    if leaked:
        await opened[0].close()  # keep a regression from hanging the worker
    assert not leaked


async def test_settle_waits_for_open_abandoned_by_cancelled_caller(tmp_path: Path):
    caller = asyncio.create_task(base._open_cancel_safe(tmp_path / "db.sqlite3"))
    await asyncio.sleep(0)
    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller
    assert base._inflight_opens

    await base.settle_abandoned_connections()

    assert not base._inflight_opens
    assert not base._pending_discards
