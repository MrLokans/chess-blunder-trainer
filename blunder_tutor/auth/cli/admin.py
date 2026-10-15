"""Operator workflows as plain async functions: typed arguments in, `AuthError` out, no
print or SystemExit, so any CLI or UI can wrap them."""

from __future__ import annotations

from blunder_tutor.auth.core.errors import (
    InviteCannotBeRegeneratedError,
    NoCredentialsIdentityError,
    UserNotFoundError,
)
from blunder_tutor.auth.core.invite import generate_invite_code
from blunder_tutor.auth.core.policies import INVITE_CODE_SETUP_KEY
from blunder_tutor.auth.core.protocols import SetupRepo
from blunder_tutor.auth.core.service import AuthService
from blunder_tutor.auth.core.types import (
    CREDENTIALS_PROVIDER_NAME,
    InviteCode,
    User,
    Username,
)


async def list_users(service: AuthService) -> list[User]:
    return await service.list_users()


async def reset_password(
    service: AuthService, username: Username, new_password: str
) -> User:
    """Also revokes all sessions."""
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

    await service.change_password(
        user_id=user.id,
        identity_id=cred_identity.id,
        new_password=new_password,
    )
    return user


async def revoke_sessions(service: AuthService, username: Username) -> User:
    user = await service.get_user_by_username(username)
    if user is None:
        raise UserNotFoundError(username)
    await service.revoke_all_sessions(user.id)
    return user


async def delete_user(service: AuthService, username: Username) -> User:
    """Fires `on_after_delete` (dir cleanup, cache eviction)."""
    user = await service.get_user_by_username(username)
    if user is None:
        raise UserNotFoundError(username)
    await service.delete_account(user.id)
    return user


async def regenerate_invite(
    service: AuthService, *, setup_repo: SetupRepo, secret_key: str
) -> InviteCode:
    """Refused once users exist: the invite gate only applies to the first user, so a new
    code would be ignored."""
    if await service.user_count() > 0:
        raise InviteCannotBeRegeneratedError()
    code = generate_invite_code(secret_key)
    await setup_repo.put(INVITE_CODE_SETUP_KEY, code)
    return code
