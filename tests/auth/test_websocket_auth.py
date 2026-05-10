"""WebSocket auth gate + per-user broadcast scoping (TREK-16).

Covers two invariants:
1. ``/ws`` rejects unauthenticated connections in credentials mode (close
   code 4401). Today's events are job updates only, so the immediate
   blast radius is small — but any per-user broadcast channel added on
   top of an open socket leaks cross-user.
2. Once authenticated, a connection only receives events scoped to its
   own ``user_id`` (matched against ``event.data["user_key"]``). Events
   without a ``user_key`` (job/cache events) are out of scope here and
   handled by TREK-130's plumbing.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from blunder_tutor.events.event_types import StatsEvent
from blunder_tutor.web.app import create_app
from blunder_tutor.web.config import config_factory
from tests.helpers.auth import TEST_BCRYPT_COST
from tests.helpers.engine import mock_engine_context

ALICE = ("alice", "password123")
BOB = ("bob", "password456")


def _set_credentials_env(monkeypatch, tmp_path: Path, *, max_users: str) -> None:
    monkeypatch.setenv("AUTH_MODE", "credentials")
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("MAX_USERS", max_users)
    monkeypatch.setenv("STOCKFISH_BINARY", "/fake/stockfish")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "main.sqlite3"))
    monkeypatch.setenv("VITE_DEV", "true")
    monkeypatch.setenv("AUTH_BCRYPT_COST", str(TEST_BCRYPT_COST))


def _build_client(
    tmp_path: Path, monkeypatch, *, max_users: str
) -> Generator[TestClient]:
    _set_credentials_env(monkeypatch, tmp_path, max_users=max_users)
    ns = argparse.Namespace(engine_path="/fake/stockfish", depth=20)
    config = config_factory(ns, dict(os.environ))
    with mock_engine_context():
        app = create_app(config)
        with TestClient(app) as client:
            yield client


@pytest.fixture
def credentials_client(tmp_path: Path, monkeypatch) -> Generator[TestClient]:
    yield from _build_client(tmp_path, monkeypatch, max_users="1")


@pytest.fixture
def credentials_client_multi(tmp_path: Path, monkeypatch) -> Generator[TestClient]:
    yield from _build_client(tmp_path, monkeypatch, max_users="2")


def _read_invite(client: TestClient) -> str:
    auth_db_path = client.app.state.auth.db_path
    with sqlite3.connect(auth_db_path) as conn:
        row = conn.execute(
            "SELECT value FROM setup WHERE key = 'invite_code'"
        ).fetchone()
    assert row is not None, "Invite code missing — bootstrap should have written it"
    return row[0]


def _signup(
    client: TestClient,
    *,
    username: str,
    password: str,
    invite: str | None = None,
) -> str:
    payload = {"username": username, "password": password}
    if invite is not None:
        payload["invite_code"] = invite
    response = client.post("/api/auth/signup", json=payload)
    response.raise_for_status()
    return response.json()["id"]


def _login(client: TestClient, *, username: str, password: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    response.raise_for_status()


def _logout(client: TestClient) -> None:
    response = client.post("/api/auth/logout")
    response.raise_for_status()


class TestWebSocketAuthGate:
    def test_unauthenticated_connect_is_rejected(self, credentials_client):
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            credentials_client.websocket_connect("/ws"),
        ):
            pass
        assert exc_info.value.code == 4401

    def test_invalid_session_cookie_is_rejected(self, credentials_client):
        credentials_client.cookies.set("session_token", "not-a-valid-token")
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            credentials_client.websocket_connect("/ws"),
        ):
            pass
        assert exc_info.value.code == 4401

    def test_authenticated_connect_can_ping(self, credentials_client):
        invite = _read_invite(credentials_client)
        username, password = ALICE
        _signup(credentials_client, username=username, password=password, invite=invite)
        with credentials_client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "ping"})
            assert ws.receive_json() == {"type": "pong"}

    def test_authenticated_connect_can_subscribe(self, credentials_client):
        invite = _read_invite(credentials_client)
        username, password = ALICE
        _signup(credentials_client, username=username, password=password, invite=invite)
        with credentials_client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "subscribe", "events": ["stats.updated"]})
            response = ws.receive_json()
        assert response["type"] == "subscribed"
        assert "stats.updated" in response["events"]

    def test_revoked_session_cookie_is_rejected(self, credentials_client):
        invite = _read_invite(credentials_client)
        username, password = ALICE
        _signup(credentials_client, username=username, password=password, invite=invite)
        stale_cookie = credentials_client.cookies.get("session_token")
        _logout(credentials_client)
        # Stale cookie survives client-side; server-side session must be gone.
        credentials_client.cookies.set("session_token", stale_cookie)
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            credentials_client.websocket_connect("/ws"),
        ):
            pass
        assert exc_info.value.code == 4401


class TestWebSocketUserScoping:
    def test_scoped_event_reaches_only_matching_user(self, credentials_client_multi):
        client = credentials_client_multi
        invite = _read_invite(client)
        alice_user, alice_pw = ALICE
        bob_user, bob_pw = BOB

        alice_id = _signup(
            client, username=alice_user, password=alice_pw, invite=invite
        )
        _logout(client)
        bob_id = _signup(client, username=bob_user, password=bob_pw)
        _logout(client)
        _login(client, username=alice_user, password=alice_pw)

        connection_manager = client.app.state.connection_manager

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "subscribe", "events": ["stats.updated"]})
            assert ws.receive_json()["type"] == "subscribed"

            # Bob's event must be filtered out; Alice's must arrive.
            client.portal.call(
                connection_manager.broadcast_event,
                StatsEvent.create_stats_updated(user_key=bob_id),
            )
            client.portal.call(
                connection_manager.broadcast_event,
                StatsEvent.create_stats_updated(user_key=alice_id),
            )
            message = ws.receive_json()

        assert message["type"] == "stats.updated"
        assert message["data"]["user_key"] == alice_id
