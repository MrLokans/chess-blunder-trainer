from __future__ import annotations

from pathlib import Path

import pytest

from blunder_tutor.auth import (
    AuthDb,
    AuthService,
    DuplicateEmailError,
    DuplicateUsernameError,
    Email,
    HmacInvitePolicy,
    InvalidInviteCodeError,
    InvalidPasswordError,
    OpenSignup,
    SqliteStorage,
    Username,
)
from tests.helpers.auth import build_test_auth_service


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


class TestSignupWithOpenPolicy:
    """The :class:`OpenSignup` invite policy — anyone may sign up,
    no invite required. Production wires :class:`HmacInvitePolicy`;
    OpenSignup is the SaaS / managed-deploy alternative kept in the
    public API for consumers that gate registration elsewhere.
    """

    @pytest.fixture
    def open_signup_service(self, auth_db: AuthDb, tmp_path: Path) -> AuthService:
        return build_test_auth_service(
            auth_db=auth_db,
            users_dir=tmp_path / "users",
            invite_policy=OpenSignup(),
        )

    async def test_signup_creates_user(self, open_signup_service: AuthService) -> None:
        user = await open_signup_service.signup(
            username=Username("alice"),
            password="password123",
        )
        assert user.username == "alice"
        assert await open_signup_service.user_count() == 1


class TestSignupWithHmacInvite:
    """The conformance promise — the full ``signup()`` surface with the
    production :class:`HmacInvitePolicy` runs end-to-end against the
    ``Storage`` protocol. Pre-TREK-59 the policy issued raw SQL on the
    txn handle, which broke any backend that didn't proxy SQL; the
    storage-agnostic consume path is what makes that contract real.
    """

    @pytest.fixture
    def hmac_service(self, auth_db: AuthDb, tmp_path: Path):
        storage = SqliteStorage(auth_db)
        service = build_test_auth_service(
            auth_db=auth_db,
            users_dir=tmp_path / "users",
            invite_policy=HmacInvitePolicy(setup_repo=storage.setup),
        )
        return service, storage

    async def test_signup_with_valid_invite_consumes_it(self, hmac_service) -> None:
        service, storage = hmac_service
        await storage.setup.put("invite_code", "stored.invite")
        user = await service.signup(
            username=Username("alice"),
            password="password123",
            invite_code="stored.invite",
        )
        assert user.username == "alice"
        # Single-use: the invite row is gone after consume.
        assert await storage.setup.get("invite_code") is None

    async def test_signup_rejects_wrong_invite(self, hmac_service) -> None:
        service, storage = hmac_service
        await storage.setup.put("invite_code", "stored.invite")
        with pytest.raises(InvalidInviteCodeError):
            await service.signup(
                username=Username("alice"),
                password="password123",
                invite_code="bogus",
            )
        # Failed consume must not have deleted the stored invite.
        assert await storage.setup.get("invite_code") == "stored.invite"

    async def test_first_user_signup_without_invite_rejected(
        self, hmac_service
    ) -> None:
        service, _storage = hmac_service
        with pytest.raises(InvalidInviteCodeError):
            await service.signup(username=Username("alice"), password="password123")

    async def test_subsequent_signup_does_not_need_invite(self, hmac_service) -> None:
        service, _storage = hmac_service
        # First user via register() bypasses the invite gate (models a
        # SaaS install where bootstrapping is done out-of-band).
        await service.register(username=Username("alice"), password="password123")
        # Second user signs up without an invite — first-user gate has
        # already passed so HmacInvitePolicy lets it through.
        bob = await service.signup(
            username=Username("bob"),
            password="password123",
        )
        assert bob.username == "bob"
