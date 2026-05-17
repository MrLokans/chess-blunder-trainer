from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from fastapi import Request

from blunder_tutor.auth import UserContext, UserId, Username
from blunder_tutor.cache.scope import user_scope
from blunder_tutor.core.dependencies import DependencyContext
from blunder_tutor.web.bypass_auth import LOCAL_USER_ID, LOCAL_USERNAME
from blunder_tutor.web.dependencies import set_request_scope


def _user_ctx(user_id: str) -> UserContext:
    return UserContext(
        user_id=UserId(user_id),
        username=Username(user_id),
        session_token=None,
    )


def _local_ctx() -> UserContext:
    return UserContext(
        user_id=LOCAL_USER_ID,
        username=LOCAL_USERNAME,
        session_token=None,
    )


def _dep_ctx(user_id: str) -> DependencyContext:
    return DependencyContext(
        db_path=Path(f"/fake/{user_id}.db"),
        event_bus=MagicMock(),
        engine_path="/fake/engine",
        user_id=UserId(user_id),
    )


def _request() -> Request:
    return Request(
        {"type": "http", "method": "GET", "path": "/api/stats", "headers": []}
    )


class TestUserScope:
    def test_credentials_user_context_returns_user_id(self):
        assert user_scope(_user_ctx("u-abc123")) == "u-abc123"

    def test_none_mode_user_context_returns_local_sentinel(self):
        assert user_scope(_local_ctx()) == "_local"

    def test_dependency_context_returns_user_id(self):
        assert user_scope(_dep_ctx("job-user-9")) == "job-user-9"


class TestSetRequestScope:
    async def test_stashes_credentials_scope_from_user_ctx(self):
        request = _request()
        request.state.user_ctx = _user_ctx("u-xyz")

        await set_request_scope(request)

        assert request.state.user_scope == "u-xyz"

    async def test_none_mode_request_scope_is_local_sentinel(self):
        request = _request()
        request.state.user_ctx = _local_ctx()

        await set_request_scope(request)

        assert request.state.user_scope == "_local"
