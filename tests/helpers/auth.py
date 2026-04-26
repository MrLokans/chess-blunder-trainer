from __future__ import annotations

from datetime import timedelta
from functools import partial
from pathlib import Path

from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.hashers import BcryptHasher
from blunder_tutor.auth.policies import HmacInvitePolicy, MaxUsersQuota
from blunder_tutor.auth.providers.credentials import CredentialsProvider
from blunder_tutor.auth.repository import IdentityRepository
from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import ValidationRules
from blunder_tutor.web.auth_hooks import (
    cleanup_user_dir,
    materialize_user_dir,
    resolve_user_db_path,
)


def build_test_auth_service(
    *,
    auth_db: AuthDb,
    users_dir: Path,
    session_max_age: timedelta = timedelta(days=30),
    session_idle: timedelta = timedelta(days=7),
    max_users: int = 1024,
) -> AuthService:
    """Construct an :class:`AuthService` with production-equivalent
    strategy wiring for tests. ``max_users`` defaults high so the cap
    is effectively off; tests that exercise the cap explicitly pass a
    smaller value (or use the credentials_app fixture which boots via
    ``MAX_USERS=1`` at the env level).
    """
    rules = ValidationRules.default()
    hasher = BcryptHasher(rules)
    identities = IdentityRepository(db=auth_db)
    return AuthService(
        auth_db=auth_db,
        db_path_resolver=partial(resolve_user_db_path, users_dir),
        providers={
            "credentials": CredentialsProvider(
                identities=identities, hasher=hasher, rules=rules
            ),
        },
        hasher=hasher,
        quota=MaxUsersQuota(max_users),
        invite_policy=HmacInvitePolicy(),
        on_after_register=partial(materialize_user_dir, users_dir),
        on_after_delete=partial(cleanup_user_dir, users_dir),
        session_max_age=session_max_age,
        session_idle=session_idle,
    )
