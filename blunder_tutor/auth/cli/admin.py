"""Library admin operations.

Async functions that drive operator workflows (list users, reset
passwords, revoke sessions, delete accounts, regenerate first-user
invite). Library callers (alternative CLIs, web admin UIs, scripts)
import these directly; the blunder_tutor argparse wrapper in
``blunder_tutor/cli/auth.py`` is one such consumer and stays thin.

Each function takes typed arguments, returns a useful value (usually
the affected user — handy for logging), and raises a typed
:class:`AuthError` subclass on failure. No SystemExit, no print.
"""

from __future__ import annotations

from blunder_tutor.auth.core.errors import (
    InviteCannotBeRegeneratedError,
    NoCredentialsIdentityError,
    UserNotFoundError,
)
from blunder_tutor.auth.core.invite import generate_invite_code
from blunder_tutor.auth.core.protocols import SetupRepo
from blunder_tutor.auth.core.service import AuthService
from blunder_tutor.auth.core.types import (
    CREDENTIALS_PROVIDER_NAME,
    InviteCode,
    User,
    Username,
)


async def list_users(service: AuthService) -> list[User]:
    """Return every registered user. Order matches
    :meth:`UserRepo.list_all` (created_at, then id) so rendering is
    deterministic across runs.
    """
    return await service.list_users()


async def reset_password(
    service: AuthService, username: Username, new_password: str
) -> User:
    """Replace the user's credentials hash and revoke every active
    session. The service hashes the password with its own configured
    :class:`PasswordHasher` so admin tools never depend on the module-
    level :func:`hash_password` shim.

    Raises :class:`UserNotFoundError` if no user matches; raises
    :class:`NoCredentialsIdentityError` if the user is OAuth-only and
    has no credential row to update.
    """
    user = await service.get_user_by_username(username)
    if user is None:
        raise UserNotFoundError(username)

    identities = await service.identities_for(user.id)
    cred_identity = next(
        (i for i in identities if i.provider == CREDENTIALS_PROVIDER_NAME),
        None,
    )
    if cred_identity is None:
        raise NoCredentialsIdentityError(username)

    await service.set_credential_hash(cred_identity.id, new_password)
    await service.revoke_all_sessions(user.id)
    return user


async def revoke_sessions(service: AuthService, username: Username) -> User:
    """Invalidate every active session for the user. Returns the user
    (the same object the caller would otherwise have to re-fetch for
    logging). Raises :class:`UserNotFoundError`.
    """
    user = await service.get_user_by_username(username)
    if user is None:
        raise UserNotFoundError(username)
    await service.revoke_all_sessions(user.id)
    return user


async def delete_user(service: AuthService, username: Username) -> User:
    """Hard-delete the user. ``AuthService.delete_account`` fires the
    consumer's ``on_after_delete`` hook (per-user dir cleanup, cache
    eviction). Raises :class:`UserNotFoundError`.
    """
    user = await service.get_user_by_username(username)
    if user is None:
        raise UserNotFoundError(username)
    await service.delete_account(user.id)
    return user


async def regenerate_invite(
    service: AuthService, *, setup_repo: SetupRepo, secret_key: str
) -> InviteCode:
    """Mint a fresh first-user invite code and write it to the setup
    store. Refuses when any user already exists — the invite gate is
    first-user-only, so a new code with users present would either be
    silently ignored by :class:`HmacInvitePolicy` (still gates on
    ``user_count``) or imply a misconfiguration the operator should
    investigate.
    """
    if await service.user_count() > 0:
        raise InviteCannotBeRegeneratedError()
    code = generate_invite_code(secret_key)
    await setup_repo.put("invite_code", code)
    return code
