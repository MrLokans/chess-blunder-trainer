from __future__ import annotations

from pathlib import Path

import pytest

from blunder_tutor.auth import (
    AuthService,
    DuplicateEmailError,
    DuplicateUsernameError,
    Email,
    InvalidPasswordError,
    Username,
)
from tests.helpers.auth import build_inmemory_auth_service


class TestRegister:
    async def test_happy_path(self, service: AuthService):
        user = await service.register(
            username=Username("alice"),
            password="password123",
            email=Email("alice@example.com"),
        )
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert await service.user_count() == 1

    async def test_without_email(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        assert user.email is None

    async def test_creates_credentials_identity(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        identities = await service.identities_for(user.id)
        assert len(identities) == 1
        assert identities[0].provider == "credentials"
        assert identities[0].provider_subject == "alice"
        assert identities[0].credential is not None

    async def test_register_is_atomic_on_dup(self, service: AuthService):
        """Register runs in a single transaction: if the second call fails
        on the uniqueness constraint, no orphaned user row or identity row
        is left behind and user_count stays at 1."""
        first = await service.register(
            username=Username("alice"), password="password123"
        )
        with pytest.raises(DuplicateUsernameError):
            await service.register(username=Username("alice"), password="another123")
        assert await service.user_count() == 1
        assert len(await service.identities_for(first.id)) == 1

    async def test_duplicate_username_raises(self, service: AuthService):
        await service.register(username=Username("alice"), password="password123")
        with pytest.raises(DuplicateUsernameError):
            await service.register(username=Username("alice"), password="another123")

    async def test_duplicate_email_raises(self, service: AuthService):
        await service.register(
            username=Username("alice"),
            password="password123",
            email=Email("alice@example.com"),
        )
        with pytest.raises(DuplicateEmailError):
            await service.register(
                username=Username("bob"),
                password="password123",
                email=Email("alice@example.com"),
            )

    async def test_password_too_short_raises(self, service: AuthService):
        with pytest.raises(InvalidPasswordError):
            await service.register(username=Username("alice"), password="short")


class TestAuthenticate:
    async def test_valid_credentials(self, service: AuthService):
        registered = await service.register(
            username=Username("alice"), password="password123"
        )
        user = await service.authenticate(
            "credentials", {"username": "alice", "password": "password123"}
        )
        assert user is not None
        assert user.id == registered.id

    async def test_wrong_password(self, service: AuthService):
        await service.register(username=Username("alice"), password="password123")
        assert (
            await service.authenticate(
                "credentials",
                {"username": "alice", "password": "wrong-password"},
            )
            is None
        )

    async def test_unknown_provider(self, service: AuthService):
        assert (
            await service.authenticate("lichess", {"code": "abc", "state": "xyz"})
            is None
        )


class TestGetUser:
    async def test_by_id(self, service: AuthService):
        registered = await service.register(
            username=Username("alice"), password="password123"
        )
        fetched = await service.get_user(registered.id)
        assert fetched is not None
        assert fetched.id == registered.id


class TestDeleteAccount:
    async def test_removes_user_row_identities_sessions(self, service: AuthService):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent="ua", ip="127.0.0.1"
        )
        assert await service.user_count() == 1

        await service.delete_account(user.id)
        assert await service.user_count() == 0
        assert await service.get_user(user.id) is None
        assert await service.resolve_session(session.token, None) is None

    async def test_removes_user_db_dir(self, service: AuthService, tmp_path: Path):
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        user_dir = tmp_path / "users" / user.id
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "main.sqlite3").touch()

        await service.delete_account(user.id)
        assert not user_dir.exists()


class TestServiceOnInMemoryStorage:
    """Smoke tests proving the service layer runs end-to-end against
    :class:`InMemoryStorage` — same API as the SQLite-backed tests
    above, just no aiosqlite, no fixtures, no transactions to disk.
    InMemory is the fast path for service-layer unit tests that don't
    care about SQL semantics; failures here mean a Protocol seam
    leaked storage assumptions.

    ``signup()`` with :class:`HmacInvitePolicy` is intentionally NOT
    covered — the policy still issues raw SQL on the transaction
    handle (see the ``HmacInvitePolicy`` docstring for the
    SetupRepo-rewrite follow-up). The InMemory helper wires
    :class:`OpenSignup` instead.
    """

    async def test_register_happy_path(self, tmp_path: Path) -> None:
        service, _ = build_inmemory_auth_service(users_dir=tmp_path / "users")
        user = await service.register(
            username=Username("alice"),
            password="password123",
            email=Email("alice@example.com"),
        )
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert await service.user_count() == 1

    async def test_register_duplicate_username_raises(self, tmp_path: Path) -> None:
        service, _ = build_inmemory_auth_service(users_dir=tmp_path / "users")
        await service.register(username=Username("alice"), password="password123")
        with pytest.raises(DuplicateUsernameError):
            await service.register(username=Username("alice"), password="another123")

    async def test_signup_with_open_policy(self, tmp_path: Path) -> None:
        service, _ = build_inmemory_auth_service(users_dir=tmp_path / "users")
        user = await service.signup(
            username=Username("alice"),
            password="password123",
        )
        assert user.username == "alice"
        assert await service.user_count() == 1

    async def test_authenticate_happy_path(self, tmp_path: Path) -> None:
        service, _ = build_inmemory_auth_service(users_dir=tmp_path / "users")
        await service.register(username=Username("alice"), password="password123")
        user = await service.authenticate(
            "credentials", {"username": "alice", "password": "password123"}
        )
        assert user is not None
        assert user.username == "alice"

    async def test_session_lifecycle(self, tmp_path: Path) -> None:
        service, _ = build_inmemory_auth_service(users_dir=tmp_path / "users")
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        session = await service.create_session(
            user_id=user.id, user_agent="ua", ip="1.2.3.4"
        )
        ctx = await service.resolve_session(session.token, ip=None)
        assert ctx is not None
        assert ctx.user_id == user.id

        await service.revoke_session(session.token)
        assert await service.resolve_session(session.token, ip=None) is None

    async def test_delete_account_cascades(self, tmp_path: Path) -> None:
        service, storage = build_inmemory_auth_service(users_dir=tmp_path / "users")
        user = await service.register(
            username=Username("alice"), password="password123"
        )
        await service.create_session(user_id=user.id, user_agent=None, ip=None)
        assert await service.user_count() == 1

        await service.delete_account(user.id)
        assert await service.user_count() == 0
        assert await storage.identities.list_for_user(user.id) == []
        assert await storage.sessions.list_for_user(user.id) == []
