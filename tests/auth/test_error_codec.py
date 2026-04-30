"""Tests for the ``build_auth_router`` factory + ``ErrorCodec`` extension
seam (TREK-57 / EPIC-3 P4.2).

Pins the contract that a consumer can override how :class:`AuthError`
subclasses surface as HTTP responses — without forking the route
handlers — by passing a custom :class:`ErrorCodec` to the factory.
"""

from __future__ import annotations

from http import HTTPStatus
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport

from blunder_tutor.auth import (
    AuthDb,
    AuthError,
    AuthService,
    DuplicateUsernameError,
    Username,
)
from blunder_tutor.auth.fastapi import (
    CookieAdapter,
    DefaultErrorCodec,
    build_auth_router,
)
from tests.helpers.auth import build_test_auth_service


def _set_test_cookie(response: Response, token: str, request: Request) -> None:
    response.set_cookie("session_token", token, httponly=True, samesite="lax")


def _clear_test_cookie(response: Response) -> None:
    response.delete_cookie("session_token")


@pytest.fixture
def service(auth_db: AuthDb, tmp_path: Path) -> AuthService:
    return build_test_auth_service(
        auth_db=auth_db,
        users_dir=tmp_path / "users",
        session_max_age=timedelta(days=1),
        session_idle=timedelta(days=1),
    )


def _make_app(service: AuthService, *, error_codec=None) -> FastAPI:
    app = FastAPI()
    app.state.auth_service = service

    def auth_service_provider(request: Request) -> AuthService:
        return request.app.state.auth_service

    router = build_auth_router(
        auth_service_provider=auth_service_provider,
        cookies=CookieAdapter(
            set_cookie=_set_test_cookie,
            clear_cookie=_clear_test_cookie,
        ),
        error_codec=error_codec,
    )
    app.include_router(router)
    return app


class TestDefaultErrorCodec:
    """The default codec preserves blunder_tutor's stable detail slugs.
    Existing API contract — no consumer override required.
    """

    async def test_duplicate_username_maps_to_409_username_taken(
        self, service: AuthService, tmp_path: Path
    ):
        await service.register(username=Username("alice"), password="password123")
        app = _make_app(service)
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            r = await client.post(
                "/api/auth/signup",
                json={"username": "alice", "password": "password123"},
            )
        assert r.status_code == HTTPStatus.CONFLICT
        assert r.json()["detail"] == "username_taken"


class TestCustomErrorCodec:
    """A consumer who wants different statuses or different detail slugs
    builds the router with their own :class:`ErrorCodec` — no route-body
    fork.
    """

    async def test_override_changes_status_and_detail(
        self, service: AuthService, tmp_path: Path
    ):
        class _Custom422Codec:
            def to_http(self, exc: AuthError) -> tuple[int, str]:
                if isinstance(exc, DuplicateUsernameError):
                    return 422, "duplicate_login"
                return DefaultErrorCodec().to_http(exc)

        await service.register(username=Username("alice"), password="password123")
        app = _make_app(service, error_codec=_Custom422Codec())
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            r = await client.post(
                "/api/auth/signup",
                json={"username": "alice", "password": "password123"},
            )
        assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert r.json()["detail"] == "duplicate_login"

    async def test_unmapped_errors_fall_through_to_default(
        self, service: AuthService, tmp_path: Path
    ):
        # A custom codec that handles only one error type still lets every
        # other AuthError surface via the default mapping. Pins that the
        # factory does not silently swallow unmapped errors.
        class _OnlyDuplicates:
            def to_http(self, exc: AuthError) -> tuple[int, str]:
                if isinstance(exc, DuplicateUsernameError):
                    return 422, "x"
                return DefaultErrorCodec().to_http(exc)

        app = _make_app(service, error_codec=_OnlyDuplicates())
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            r = await client.post(
                "/api/auth/signup",
                json={"username": "??", "password": "password123"},
            )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert r.json()["detail"] == "invalid_username"
