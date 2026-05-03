"""Integration tests for per-user JobExecutor + BackgroundScheduler in
``AUTH_MODE=credentials`` (TREK-38).

Acceptance criteria:
- ``app.state.{job_executor, scheduler}`` are non-None in credentials mode.
- POST /api/import/pgn runs to completion within seconds.
- Two concurrent users — no DB cross-talk and no shared job rows.
- Auto-sync fanout dispatches sync jobs only for users whose settings say so.
"""

from __future__ import annotations

import asyncio
import shutil
import sqlite3
from contextlib import closing
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from blunder_tutor.auth import UserId
from blunder_tutor.background.scheduler import (
    _fanout_tick,
    _is_sync_due,
    _maybe_dispatch_sync_for_user,
)
from blunder_tutor.core.dependencies import (
    DependencyContext,
    clear_context,
    set_context,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType, JobExecutionRequestEvent
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.utils.time import now_iso
from blunder_tutor.web.bypass_auth import LOCAL_USER_ID
from tests.auth.conftest import (
    DEFAULT_PASSWORD,
    signup_via_http,
)

VALID_PGN = """[Event "Test"]
[Site "Test"]
[Date "2024.01.01"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O 1-0"""

VALID_PGN_2 = """[Event "Test2"]
[Site "Test"]
[Date "2024.01.02"]
[White "PlayerA"]
[Black "PlayerB"]
[Result "0-1"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 0-1"""


async def _wait_for_job(
    client: httpx.AsyncClient, job_id: str, *, timeout_s: float = 10.0
) -> dict:
    """Poll /api/import/status/{job_id} until status is terminal or
    timeout elapses. Returns the final status payload.
    """
    deadline = asyncio.get_running_loop().time() + timeout_s
    last = {}
    while asyncio.get_running_loop().time() < deadline:
        resp = await client.get(f"/api/import/status/{job_id}")
        if resp.status_code == HTTPStatus.OK:
            last = resp.json()
            if last.get("status") in ("completed", "failed"):
                return last
        await asyncio.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish in {timeout_s}s — last={last}")


def _assert_job_in_exactly_one_db(job_id: str, db_a: Path, db_b: Path) -> None:
    present = []
    for db in (db_a, db_b):
        # `with sqlite3.connect(...)` only commits/rollbacks — it does NOT
        # close the connection; `closing()` is what actually releases it.
        with closing(sqlite3.connect(db)) as conn:
            row = conn.execute(
                "SELECT 1 FROM background_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is not None:
                present.append(db)
    assert len(present) == 1, (
        f"job {job_id} should live in exactly one user DB, found in {present}"
    )


class TestBackgroundWiring:
    async def test_executor_and_scheduler_constructed_in_credentials_mode(
        self, credentials_app: FastAPI
    ):
        assert credentials_app.state.job_executor is not None
        assert credentials_app.state.scheduler is not None
        assert credentials_app.state.scheduler.scheduler.running


class TestImportPgnRunsToCompletion:
    async def test_post_import_pgn_completes(
        self,
        client_credentials_mode: httpx.AsyncClient,
        invite_code: str,
    ):
        signup = await signup_via_http(client_credentials_mode, invite_code)
        assert signup.status_code == HTTPStatus.OK, signup.text

        resp = await client_credentials_mode.post(
            "/api/import/pgn", json={"pgn": VALID_PGN}
        )
        assert resp.status_code == HTTPStatus.OK, resp.text
        body = resp.json()
        assert body["success"] is True
        job_id = body["job_id"]

        final = await _wait_for_job(client_credentials_mode, job_id)
        assert final["status"] == "completed", final


class TestTwoUserJobIsolation:
    async def test_user_a_jobs_do_not_appear_in_user_b_db(
        self, credentials_app_multi: FastAPI, invite_code: str, tmp_path: Path
    ):
        # Two clients ⇒ two independent cookie jars.
        transport = ASGITransport(app=credentials_app_multi)

        async with (
            httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client_a,
            httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client_b,
        ):
            r1 = await signup_via_http(
                client_a, invite_code, username="alice", password=DEFAULT_PASSWORD
            )
            assert r1.status_code == HTTPStatus.OK, r1.text
            r2 = await signup_via_http(
                client_b, invite_code, username="bob", password=DEFAULT_PASSWORD
            )
            assert r2.status_code == HTTPStatus.OK, r2.text

            ra = await client_a.post("/api/import/pgn", json={"pgn": VALID_PGN})
            rb = await client_b.post("/api/import/pgn", json={"pgn": VALID_PGN_2})
            assert ra.status_code == HTTPStatus.OK and rb.status_code == HTTPStatus.OK
            job_a = ra.json()["job_id"]
            job_b = rb.json()["job_id"]

            await _wait_for_job(client_a, job_a)
            await _wait_for_job(client_b, job_b)

            # Each user can read their own job; the other user's job is a 404.
            self_a = await client_a.get(f"/api/import/status/{job_a}")
            self_b = await client_b.get(f"/api/import/status/{job_b}")
            cross_ab = await client_a.get(f"/api/import/status/{job_b}")
            cross_ba = await client_b.get(f"/api/import/status/{job_a}")
            assert self_a.status_code == HTTPStatus.OK
            assert self_b.status_code == HTTPStatus.OK
            assert cross_ab.status_code == HTTPStatus.NOT_FOUND, (
                "user A must not see user B's job"
            )
            assert cross_ba.status_code == HTTPStatus.NOT_FOUND, (
                "user B must not see user A's job"
            )

            # And the row really lives in only one DB.
            users_dir = credentials_app_multi.state.auth.users_dir
            user_dirs = sorted(p for p in users_dir.iterdir() if p.is_dir())
            assert len(user_dirs) == 2
            db_a, db_b = (p / "main.sqlite3" for p in user_dirs)
            _assert_job_in_exactly_one_db(job_a, db_a, db_b)
            _assert_job_in_exactly_one_db(job_b, db_a, db_b)


class TestFanoutSchedulerDispatchesPerUser:
    """The fanout tick reads each user's settings on its own DB, so a
    user with auto-sync enabled gets a sync job dispatched while a user
    with auto-sync disabled does not. Post-EPIC-6 (TREK-108): dispatch
    is per-(user, profile) — alice needs a tracked profile to fire any
    events, and bob's global kill-switch suppresses dispatch regardless
    of whether he has a profile.
    """

    async def test_dispatch_only_when_due_and_enabled(
        self, credentials_app_multi: FastAPI, invite_code: str
    ):
        transport = ASGITransport(app=credentials_app_multi)
        async with (
            httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client_a,
            httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client_b,
        ):
            signup_a = await signup_via_http(client_a, invite_code, username="alice")
            await signup_via_http(client_b, invite_code, username="bob")
            alice_user_id = signup_a.json()["id"]
            # Alice opts in to auto-sync; Bob opts out.
            await client_a.post(
                "/api/settings",
                json={
                    "auto_sync": True,
                    "sync_interval": 24,
                    "max_games": 10,
                    "auto_analyze": False,
                    "spaced_repetition_days": 30,
                },
            )
            await client_b.post(
                "/api/settings",
                json={
                    "auto_sync": False,
                    "sync_interval": 24,
                    "max_games": 10,
                    "auto_analyze": False,
                    "spaced_repetition_days": 30,
                },
            )

            users_dir = credentials_app_multi.state.auth.users_dir
            # Seed alice with a tracked profile via her per-user DB. Per-
            # (user, profile) dispatch (TREK-108) needs at least one
            # profile per user with `auto_sync_enabled = 1` to fire — the
            # API path would also do an upstream existence check we want
            # to avoid in this scheduler-focused test. `repo.create` inserts
            # a `profile_preferences` row with the default
            # `auto_sync_enabled = 1`; if that default ever flips, this
            # test silently changes meaning and should be revisited.
            alice_db = users_dir / alice_user_id / "main.sqlite3"
            async with SqliteProfileRepository(alice_db) as alice_profiles:
                await alice_profiles.create("lichess", "alice_chess", make_primary=True)

            user_dirs = sorted(p for p in users_dir.iterdir() if p.is_dir())
            event_bus: EventBus = credentials_app_multi.state.event_bus

            # Subscribe BEFORE dispatch so we observe the published event.
            queue = await event_bus.subscribe(EventType.JOB_EXECUTION_REQUESTED)

            # Drive one tick worth of dispatch work for each user. We do
            # not invoke APScheduler — testing the body in isolation
            # avoids a real-time wait.
            try:
                for user_dir in user_dirs:
                    user_id = UserId(user_dir.name)
                    set_context(
                        DependencyContext(
                            db_path=user_dir / "main.sqlite3",
                            event_bus=event_bus,
                            engine_path=credentials_app_multi.state.config.engine_path,
                            user_id=user_id,
                        )
                    )
                    try:
                        await _maybe_dispatch_sync_for_user(
                            event_bus=event_bus, user_id=user_id
                        )
                    finally:
                        clear_context()
            finally:
                await event_bus.unsubscribe(queue, EventType.JOB_EXECUTION_REQUESTED)

            dispatched_user_ids: list[str] = []
            while not queue.empty():
                evt = queue.get_nowait()
                if evt.data.get("job_type") == "sync":
                    dispatched_user_ids.append(evt.data["user_id"])

            # Exactly one dispatch — Alice's. Bob's auto-sync is off.
            assert len(dispatched_user_ids) == 1, dispatched_user_ids
            assert dispatched_user_ids[0] == alice_user_id


class TestSyncDuePredicate:
    @pytest.mark.parametrize(
        ("last", "interval", "expected"),
        [
            (None, 24, True),
            ("", 24, True),
            ("not-a-timestamp", 24, True),
            ("2020-01-01T00:00:00", 24, True),
        ],
    )
    def test_due_when_missing_or_old(self, last, interval, expected):
        assert _is_sync_due(last, interval) is expected

    def test_not_due_when_recent(self):
        recent = now_iso()
        assert _is_sync_due(recent, 24) is False


class TestDeleteRaceGuard:
    """``delete_account`` rmtrees ``users/<uid>/``. A fanout tick or an
    in-flight executor task that holds the (now stale) user_id must NOT
    re-create the directory via the auto-mkdir in
    ``analysis.db._connect_async``. The guard is the
    ``db_path.parent.exists()`` check at both call sites.
    """

    async def test_executor_skips_event_for_deleted_user(
        self,
        credentials_app: FastAPI,
        invite_code: str,
        client_credentials_mode: httpx.AsyncClient,
    ):
        signup = await signup_via_http(client_credentials_mode, invite_code)
        assert signup.status_code == HTTPStatus.OK
        user_id_str = signup.json()["id"]

        users_dir: Path = credentials_app.state.auth.users_dir
        user_dir = users_dir / user_id_str
        assert user_dir.exists()
        shutil.rmtree(user_dir)

        event_bus: EventBus = credentials_app.state.event_bus
        evt = JobExecutionRequestEvent.create(
            job_id="ghost-job-id",
            job_type="sync",
            user_id=UserId(user_id_str),
        )

        await event_bus.publish(evt)
        await asyncio.sleep(0.2)

        # The behavioural invariant: the executor MUST NOT recreate the
        # deleted user's data directory or DB file. The skip-log is
        # informational; behaviour is what matters here.
        assert not user_dir.exists()
        assert not (user_dir / "main.sqlite3").exists()

    async def test_fanout_tick_skips_deleted_user(
        self, credentials_app: FastAPI, invite_code: str
    ):
        transport = ASGITransport(app=credentials_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            signup = await signup_via_http(client, invite_code)
            assert signup.status_code == HTTPStatus.OK
            user_id_str = signup.json()["id"]

        users_dir: Path = credentials_app.state.auth.users_dir
        user_dir = users_dir / user_id_str
        shutil.rmtree(user_dir)

        async def stale_lister() -> list[UserId]:
            return [UserId(user_id_str)]

        def resolver(uid: UserId) -> Path:
            return users_dir / uid / "main.sqlite3"

        await _fanout_tick(
            event_bus=credentials_app.state.event_bus,
            engine_path=credentials_app.state.config.engine_path,
            list_users=stale_lister,
            db_path_resolver=resolver,
        )

        assert not user_dir.exists()


class TestNoneModeUserListSentinel:
    """Smoke test: in none-mode, the user-list callable yields the
    synthetic ``_local`` id so the executor + scheduler operate
    uniformly across both auth modes.
    """

    def test_local_user_id_constant(self):
        assert LOCAL_USER_ID == "_local"
