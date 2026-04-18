from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from blunder_tutor.auth.service import AuthService
from blunder_tutor.auth.types import (
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
from blunder_tutor.web.config import AppConfig
from blunder_tutor.web.dependencies import ConfigDep, get_user_context
from blunder_tutor.web.middleware import invalidate_setup_cache

router = APIRouter(prefix="/api/auth")


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
    svc: AuthService | None = request.app.state.auth_service
    if svc is None:
        # Credentials mode not active — auth endpoints are offline.
        raise HTTPException(status_code=404)
    return svc


def _get_optional_user_context(request: Request) -> UserContext | None:
    """Logout-style routes should be idempotent — a client calling
    ``/api/auth/logout`` without a live session gets a clean 204, not a
    confusing 401. This dependency mirrors ``get_user_context`` but never
    raises.
    """
    return getattr(request.state, "user_ctx", None)


def _cookie_secure(config: AppConfig, request: Request) -> bool:
    """Session cookie `secure` flag.

    Precedence:
    1. Explicit ``AUTH_COOKIE_SECURE`` override (for prod behind a
       TLS-terminating proxy that doesn't forward ``X-Forwarded-Proto``
       or where ``request.url.scheme`` still reads ``http``).
    2. Request scheme ``https`` → ``True``.
    3. Dev mode (``vite_dev``) → ``False``.
    4. Fallback ``False`` so ``http`` responses don't drop the cookie at
       the browser, though this is a misconfiguration worth flagging in
       an ops guide.
    """
    if config.auth.cookie_secure is not None:
        return config.auth.cookie_secure
    if request.url.scheme == "https":
        return True
    if config.vite_dev:
        return False
    return False


def _set_session_cookie(
    response: Response, token: str, max_age_seconds: int, *, secure: bool
) -> None:
    response.set_cookie(
        "session_token",
        token,
        max_age=max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


@router.post("/signup", response_model=MeResponse)
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
            max_users=config.auth.max_users,
            email=email,
            invite_code=body.invite_code,
            secret_key=config.auth.secret_key,
        )
    except UserCapReachedError as exc:
        raise HTTPException(status_code=403, detail="user_cap_reached") from exc
    except InvalidInviteCodeError as exc:
        # Don't split "missing" / "rotated" / "hmac" into distinct
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

    session = await service.create_session(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_session_cookie(
        response,
        session.token,
        config.auth.session_max_age_seconds,
        secure=_cookie_secure(config, request),
    )
    return MeResponse(id=user.id, username=user.username, email=user.email)


@router.post("/login", response_model=MeResponse)
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
        raise HTTPException(status_code=401, detail="invalid_credentials")

    session = await service.create_session(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    _set_session_cookie(
        response,
        session.token,
        config.auth.session_max_age_seconds,
        secure=_cookie_secure(config, request),
    )
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
    response.delete_cookie("session_token", path="/")


@router.post("/logout-all", status_code=204)
async def logout_all(
    ctx: Annotated[UserContext | None, Depends(_get_optional_user_context)],
    response: Response,
    service: Annotated[AuthService, Depends(_get_service)],
) -> None:
    if ctx is not None:
        await service.revoke_all_sessions(ctx.user_id)
    response.delete_cookie("session_token", path="/")


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
    invalidate_setup_cache(request, ctx.user_id)
    locale_cache: dict[str, str] | None = getattr(
        request.app.state, "_locale_cache", None
    )
    if locale_cache is not None:
        locale_cache.pop(ctx.user_id, None)

    await service.delete_account(ctx.user_id)
    response.delete_cookie("session_token", path="/")
