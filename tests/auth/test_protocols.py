from __future__ import annotations

from typing import TYPE_CHECKING

from blunder_tutor.auth import (
    AuthProvider,
    BcryptHasher,
    CredentialsProvider,
    HmacInvitePolicy,
    IdentityRepo,
    IdentityRepository,
    InvitePolicy,
    MaxUsersQuota,
    NoQuota,
    OpenSignup,
    PasswordHasher,
    QuotaPolicy,
    SessionRepo,
    SessionRepository,
    SetupRepo,
    SetupRepository,
    UserRepo,
    UserRepository,
    ValidationRules,
)

if TYPE_CHECKING:
    from blunder_tutor.auth import AuthDb


class TestProtocolConformance:
    """Static structural checks: every concrete class must satisfy the
    matching Protocol so a backend swap (P2.2 InMemory, future Postgres)
    is an isolated change at the consumer wiring site, not a service-
    layer rewrite. Failures here surface at *type-check* / *import*
    time, not at runtime — that's the whole point of formal Protocols.
    """

    def test_repositories_satisfy_repo_protocols(self, auth_db: AuthDb) -> None:
        users: UserRepo = UserRepository(db=auth_db)
        identities: IdentityRepo = IdentityRepository(db=auth_db)
        sessions: SessionRepo = SessionRepository(db=auth_db)
        setup: SetupRepo = SetupRepository(db=auth_db)
        # The annotated assignments above are the actual contract check;
        # touch the values here so the binding isn't dead-code-eliminated
        # by an over-eager static analyzer.
        assert all(repo is not None for repo in (users, identities, sessions, setup))

    def test_bcrypt_hasher_satisfies_password_hasher(self) -> None:
        hasher: PasswordHasher = BcryptHasher(ValidationRules.default())
        assert hasher is not None

    def test_quota_policies_satisfy_quota_protocol(self) -> None:
        capped: QuotaPolicy = MaxUsersQuota(max_users=5)
        unlimited: QuotaPolicy = NoQuota()
        assert capped is not None
        assert unlimited is not None

    def test_invite_policies_satisfy_invite_protocol(self) -> None:
        from blunder_tutor.auth import InMemoryStorage

        storage = InMemoryStorage()
        hmac_first_user: InvitePolicy = HmacInvitePolicy(setup_repo=storage.setup)
        open_: InvitePolicy = OpenSignup()
        assert hmac_first_user is not None
        assert open_ is not None

    def test_credentials_provider_satisfies_auth_provider(
        self, auth_db: AuthDb
    ) -> None:
        rules = ValidationRules.default()
        provider: AuthProvider = CredentialsProvider(
            identities=IdentityRepository(db=auth_db),
            hasher=BcryptHasher(rules),
            rules=rules,
        )
        assert provider is not None
