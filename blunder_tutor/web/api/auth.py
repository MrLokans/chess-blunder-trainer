from __future__ import annotations

import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_throttle import RateLimiter
from pydantic import BaseModel

from blunder_tutor.auth import (
    AuthService,
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidEmailError,
    InvalidInviteCodeError,
    InvalidPasswordError,
    InvalidUsernameError,
    UserCapReachedError,
    UserContext,
    make_email,
    make_username,
)
from blunder_tutor.auth.fastapi import get_user_context
from blunder_tutor.web.cookies import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from blunder_tutor.web.dependencies import ConfigDep

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")


async def _login_rate_limit(request: Request, response: Response) -> None:
    limiter: RateLimiter = request.app.state.login_rate_limiter
    await limiter(request, response)


async def _signup_rate_limit(request: Request, response: Response) -> None:
    limiter: RateLimiter = request.app.state.signup_rate_limiter
    await limiter(request, response)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _revoke_caller_cookie(request: Request, service: AuthService) -> None:
    # OWASP V7: a privilege change must terminate the previous session
    # in addition to issuing a new ID. Best-effort by design — a transient
    # DB failure here must not block the legitimate login / signup flow.
    old_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not old_token:
        return
    try:
        await service.revoke_session(old_token)
    except sqlite3.Error:
        log.warning(
            "auth.session.revoke_pre_existing.failed ip=%s",
            _client_ip(request),
            exc_info=True,
        )


class SignupRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    invite_code: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    id: str
    username: str
    email: str | None = None


def _get_service(request: Request) -> AuthService:
    auth = request.app.state.auth
    if auth is None:
        # Credentials mode not active — auth endpoints are offline.
        raise HTTPException(status_code=404)
    return auth.service


def _get_optional_user_context(request: Request) -> UserContext | None:
    """Logout-style routes should be idempotent — a client calling
    ``/api/auth/logout`` without a live session gets a clean 204, not a
    confusing 401. This dependency mirrors ``get_user_context`` but never
    raises.
    """
    return getattr(request.state, "user_ctx", None)


@router.post(
    "/signup",
    response_model=MeResponse,
    dependencies=[Depends(_signup_rate_limit)],
)
async def signup(
    request: Request,
    body: SignupRequest,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
    config: ConfigDep,
) -> MeResponse:
    try:
        username = make_username(body.username)
        email = make_email(body.email) if body.email else None
    except InvalidUsernameError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc
    except InvalidEmailError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc

    try:
        user = await service.signup(
            username=username,
            password=body.password,
            email=email,
            invite_code=body.invite_code,
        )
    except UserCapReachedError as exc:
        raise HTTPException(status_code=403, detail="user_cap_reached") from exc
    except InvalidInviteCodeError as exc:
        # Don't split "missing" / "rotated" / "not_issued" into distinct
        # statuses — a single response shape avoids an enumeration
        # oracle on the invite slot.
        detail = (
            "invite_code_required"
            if str(exc.offender) == "missing"
            else "invite_code_invalid"
        )
        raise HTTPException(status_code=403, detail=detail) from exc
    except DuplicateUsernameError as exc:
        raise HTTPException(status_code=409, detail="username_taken") from exc
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail="email_taken") from exc
    except InvalidPasswordError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc

    await _revoke_caller_cookie(request, service)
    session = await service.create_session(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    set_session_cookie(response, session.token, config, request)
    return MeResponse(id=user.id, username=user.username, email=user.email)


@router.post(
    "/login",
    response_model=MeResponse,
    dependencies=[Depends(_login_rate_limit)],
)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
    config: ConfigDep,
) -> MeResponse:
    # Pass the raw username straight through: `CredentialsProvider` runs
    # `make_username` internally and consumes bcrypt dummy time on shape
    # failure, keeping "malformed input" indistinguishable from "unknown
    # user" on the wall clock. Validating here first would re-introduce a
    # timing fork.
    user = await service.authenticate(
        "credentials",
        {"username": body.username, "password": body.password},
    )
    if user is None:
        log.warning(
            "auth.login.failed ip=%s username=%r",
            _client_ip(request),
            body.username,
        )
        raise HTTPException(status_code=401, detail="invalid_credentials")

    await _revoke_caller_cookie(request, service)
    session = await service.create_session(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    set_session_cookie(response, session.token, config, request)
    return MeResponse(id=user.id, username=user.username, email=user.email)


@router.post("/logout", status_code=204)
async def logout(
    ctx: Annotated[UserContext | None, Depends(_get_optional_user_context)],
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> None:
    if ctx is not None and ctx.is_authenticated:
        assert ctx.session_token is not None
        await service.revoke_session(ctx.session_token)
    clear_session_cookie(response)


@router.post("/logout-all", status_code=204)
async def logout_all(
    ctx: Annotated[UserContext | None, Depends(_get_optional_user_context)],
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> None:
    if ctx is not None:
        await service.revoke_all_sessions(ctx.user_id)
    clear_session_cookie(response)


@router.get("/me", response_model=MeResponse)
async def me(
    ctx: Annotated[UserContext, Depends(get_user_context)],
    service: Annotated[AuthService, Depends(_get_service)],
) -> MeResponse:
    user = await service.get_user(ctx.user_id)
    if user is None:
        raise HTTPException(status_code=401)
    return MeResponse(id=user.id, username=user.username, email=user.email)


@router.delete("/account", status_code=204)
async def delete_account(
    request: Request,
    ctx: Annotated[UserContext, Depends(get_user_context)],
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> None:
    # Evict per-user entries in app-level caches BEFORE the account is
    # gone so nothing can race on a read after the user_id dies. Cache
    # keys are the raw uuid hex so new users cannot collide.
    request.app.state.setup_completed_cache.invalidate(ctx.user_id)
    request.app.state.locale_cache.invalidate(ctx.user_id)
    request.app.state.features_cache.invalidate(ctx.user_id)

    await service.delete_account(ctx.user_id)
    clear_session_cookie(response)
