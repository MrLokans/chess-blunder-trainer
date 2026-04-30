"""Factory for the auth API routes.

Replaces the module-level ``router = APIRouter(prefix="/api/auth")``
constant in blunder_tutor with a function that takes the per-app
specifics — auth-service lookup, cookie-set/clear that knows about
the consumer's TLS posture, error codec, response factories, rate
limiters — and returns a fully wired :class:`APIRouter`.

Consumers wrap the factory with their own glue:

.. code-block:: python

    router = build_auth_router(
        auth_service_provider=lambda req: req.app.state.auth.service,
        cookies=CookieAdapter(
            set_cookie=set_cookie_with_app_config,
            clear_cookie=clear_session_cookie,
            name=SESSION_COOKIE_NAME,
        ),
        login_dependencies=[Depends(login_rate_limit)],
        signup_dependencies=[Depends(signup_rate_limit)],
    )
    app.include_router(router)
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from blunder_tutor.auth.core.errors import AuthError
from blunder_tutor.auth.core.protocols import ErrorCodec
from blunder_tutor.auth.core.service import AuthService
from blunder_tutor.auth.core.types import (
    CREDENTIALS_PROVIDER_NAME,
    User,
    UserContext,
    make_email,
    make_username,
)
from blunder_tutor.auth.fastapi.cookies import SESSION_COOKIE_NAME
from blunder_tutor.auth.fastapi.dependencies import get_user_context
from blunder_tutor.auth.fastapi.errors import DefaultErrorCodec

log = logging.getLogger(__name__)


# Real callable types so a wrong-shape consumer-supplied callable
# fails type-checking at the wiring site instead of at request time.
type AuthServiceProvider = Callable[[Request], AuthService]
type SetSessionCookie = Callable[[Response, str, Request], None]
type ClearSessionCookie = Callable[[Response], None]
type MeResponseFactory = Callable[[User], BaseModel]


@dataclass(frozen=True, kw_only=True)
class CookieAdapter:
    """Cookie I/O bound to the consumer's TLS posture.

    ``set_cookie`` is called with ``(response, token, request)`` so the
    consumer can flip ``Secure``/``SameSite`` based on the originating
    request. ``clear_cookie`` is called on the response only.
    """

    set_cookie: SetSessionCookie
    clear_cookie: ClearSessionCookie
    name: str = SESSION_COOKIE_NAME


class SignupRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    invite_code: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    """Default body for ``GET /me`` and the success payload for
    ``signup`` / ``login``. Override via the ``me_response_factory``
    parameter of :func:`build_auth_router` if a consumer needs a
    different shape (e.g. role claims, tenant id, profile fields).
    """

    id: str
    username: str
    email: str | None = None


def _default_me_factory(user: User) -> MeResponse:
    return MeResponse(id=user.id, username=user.username, email=user.email)


@dataclass(frozen=True)
class _RouterCtx:
    """Per-app wiring shared by every route handler in the factory."""

    auth_service_provider: AuthServiceProvider
    cookies: CookieAdapter
    codec: ErrorCodec
    me_factory: MeResponseFactory


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _raise_from_auth_error(codec: ErrorCodec, exc: AuthError) -> NoReturn:
    http_status, detail = codec.to_http(exc)
    raise HTTPException(status_code=http_status, detail=detail) from exc


async def _revoke_caller_cookie(
    request: Request, service: AuthService, cookie_name: str
) -> None:
    # OWASP V7: a privilege change must terminate the previous
    # session in addition to issuing a new ID. Best-effort —
    # transient storage failures here must not block the legitimate
    # login / signup flow.
    old_token = request.cookies.get(cookie_name)
    if not old_token:
        return
    try:
        await service.revoke_session(old_token)
    except Exception:
        log.warning(
            "auth.session.revoke_pre_existing.failed",
            exc_info=True,
        )


async def _issue_session_cookie(
    ctx: _RouterCtx,
    request: Request,
    response: Response,
    service: AuthService,
    user: User,
) -> None:
    await _revoke_caller_cookie(request, service, ctx.cookies.name)
    session = await service.create_session(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
    )
    ctx.cookies.set_cookie(response, session.token, request)


async def _do_signup(
    ctx: _RouterCtx,
    request: Request,
    body: SignupRequest,
    response: Response,
    service: AuthService,
) -> BaseModel:
    try:
        username = make_username(body.username)
        email = make_email(body.email) if body.email else None
        user = await service.signup(
            username=username,
            password=body.password,
            email=email,
            invite_code=body.invite_code,
        )
    except AuthError as exc:
        _raise_from_auth_error(ctx.codec, exc)
    await _issue_session_cookie(ctx, request, response, service, user)
    return ctx.me_factory(user)


async def _do_login(
    ctx: _RouterCtx,
    request: Request,
    body: LoginRequest,
    response: Response,
    service: AuthService,
) -> BaseModel:
    # Pass the raw username straight through: ``CredentialsProvider``
    # runs ``make_username`` internally and consumes bcrypt dummy
    # time on shape failure, keeping "malformed input" indistinguishable
    # from "unknown user" on the wall clock.
    user = await service.authenticate(
        CREDENTIALS_PROVIDER_NAME,
        {"username": body.username, "password": body.password},
    )
    if user is None:
        log.warning(
            "auth.login.failed ip=%s username=%r",
            _client_ip(request),
            body.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        )
    await _issue_session_cookie(ctx, request, response, service, user)
    return ctx.me_factory(user)


def build_auth_router(
    *,
    auth_service_provider: AuthServiceProvider,
    cookies: CookieAdapter,
    error_codec: ErrorCodec | None = None,
    me_response_factory: MeResponseFactory | None = None,
    login_dependencies: Sequence[Any] = (),
    signup_dependencies: Sequence[Any] = (),
    prefix: str = "/api/auth",
) -> APIRouter:
    """Build the auth API router.

    All blunder_tutor-specific bits flow through the parameters so a
    different consumer can swap any individual piece without forking
    the route bodies. The router keeps the existing six-route surface:
    ``signup``, ``login``, ``logout``, ``logout-all``, ``me``,
    ``account``.

    Cache invalidation on account delete is the consumer's job —
    compose it into ``AuthService.on_after_delete`` at construction
    time. The route handler itself only revokes the session cookie
    after the service call returns.
    """
    ctx = _RouterCtx(
        auth_service_provider=auth_service_provider,
        cookies=cookies,
        codec=error_codec or DefaultErrorCodec(),
        me_factory=me_response_factory or _default_me_factory,
    )

    # Every endpoint reaches the per-app wiring through `ctx` (closed
    # over by the inner functions). The closure-style factory is what
    # lets a consumer swap any piece (TLS posture, rate limits, error
    # shape) without forking the route bodies.
    def _get_service(request: Request) -> AuthService:
        return ctx.auth_service_provider(request)

    def _get_optional_user_context(request: Request) -> UserContext | None:
        # Logout-style routes are idempotent: a client calling
        # ``/logout`` without a live session gets a clean 204, not a
        # confusing 401.
        return getattr(request.state, "user_ctx", None)

    router = APIRouter(prefix=prefix)

    @router.post("/signup", dependencies=[Depends(d) for d in signup_dependencies])
    async def signup(
        request: Request,
        body: SignupRequest,
        response: Response,
        service: Annotated[AuthService, Depends(_get_service)],
    ):
        return await _do_signup(ctx, request, body, response, service)

    @router.post("/login", dependencies=[Depends(d) for d in login_dependencies])
    async def login(
        request: Request,
        body: LoginRequest,
        response: Response,
        service: Annotated[AuthService, Depends(_get_service)],
    ):
        return await _do_login(ctx, request, body, response, service)

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(
        user_ctx: Annotated[UserContext | None, Depends(_get_optional_user_context)],
        response: Response,
        service: Annotated[AuthService, Depends(_get_service)],
    ) -> None:
        if user_ctx is not None and user_ctx.is_authenticated:
            assert user_ctx.session_token is not None
            await service.revoke_session(user_ctx.session_token)
        ctx.cookies.clear_cookie(response)

    @router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
    async def logout_all(
        user_ctx: Annotated[UserContext | None, Depends(_get_optional_user_context)],
        response: Response,
        service: Annotated[AuthService, Depends(_get_service)],
    ) -> None:
        if user_ctx is not None:
            await service.revoke_all_sessions(user_ctx.user_id)
        ctx.cookies.clear_cookie(response)

    @router.get("/me")
    async def me(
        user_ctx: Annotated[UserContext, Depends(get_user_context)],
        service: Annotated[AuthService, Depends(_get_service)],
    ):
        user = await service.get_user(user_ctx.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return ctx.me_factory(user)

    @router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_account(
        user_ctx: Annotated[UserContext, Depends(get_user_context)],
        response: Response,
        service: Annotated[AuthService, Depends(_get_service)],
    ) -> None:
        # Cache eviction / per-user-dir cleanup belongs in the
        # ``on_after_delete`` hook on :class:`AuthService` — the route
        # only handles the cookie. Composition happens at consumer
        # wiring time.
        await service.delete_account(user_ctx.user_id)
        ctx.cookies.clear_cookie(response)

    return router
