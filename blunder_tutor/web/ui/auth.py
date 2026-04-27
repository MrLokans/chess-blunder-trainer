from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from blunder_tutor.auth import AuthService, UserContext
from blunder_tutor.auth.fastapi import clear_session_cookie
from blunder_tutor.repositories.settings import SettingsRepository

auth_ui_router = APIRouter()


def _service(request: Request) -> AuthService | None:
    auth = getattr(request.app.state, "auth", None)
    return auth.service if auth is not None else None


def _ctx(request: Request) -> UserContext | None:
    return getattr(request.state, "user_ctx", None)


def _is_authenticated(request: Request) -> bool:
    ctx = _ctx(request)
    return ctx is not None and ctx.is_authenticated


@auth_ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    service = _service(request)
    if service is None:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    if _is_authenticated(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "login.html", {})


@auth_ui_router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    service = _service(request)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if _is_authenticated(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    count = await service.user_count()
    if count == 0:
        # First user must come through the invite-gated /setup flow.
        return RedirectResponse(url="/setup", status_code=status.HTTP_302_FOUND)
    templates = request.app.state.templates
    config = request.app.state.config
    if count >= config.auth.max_users:
        return templates.TemplateResponse(
            request, "signup_full.html", {}, status_code=status.HTTP_403_FORBIDDEN
        )
    return templates.TemplateResponse(request, "signup.html", {})


@auth_ui_router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Dispatch between the credentials-mode first-user invite page and
    the legacy platform-setup page (Lichess / Chess.com username + initial
    import). Pre-auth era had a single `/setup` route; this handler
    preserves it while layering the new first-user flow on top.
    """
    service = _service(request)
    ctx = _ctx(request)
    templates = request.app.state.templates

    if service is not None:
        count = await service.user_count()
        if count == 0:
            return templates.TemplateResponse(request, "first_setup.html", {})
        if ctx is None or not ctx.is_authenticated:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # `UserDbPathMiddleware` populates `user_db_path` from the per-mode
    # resolver — credentials-mode ⇒ the signed-in user's DB, none-mode
    # ⇒ the legacy single-user DB.
    db_path: Path = request.state.user_db_path

    async with SettingsRepository(db_path=db_path) as settings_repo:
        if await settings_repo.is_setup_completed():
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(request, "setup.html", {})


@auth_ui_router.post("/logout")
async def logout_ui(request: Request):
    """Browser-friendly logout: revokes the session and redirects to
    ``/login`` (credentials mode) or ``/`` (none mode). The JSON API at
    ``/api/auth/logout`` stays available for programmatic callers.
    """
    service = _service(request)
    ctx = _ctx(request)
    if service is not None and ctx is not None and ctx.is_authenticated:
        # ctx.session_token is non-None by ctx.is_authenticated; narrow for mypy.
        assert ctx.session_token is not None
        await service.revoke_session(ctx.session_token)

    target = "/login" if service is not None else "/"
    response = RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(response)
    return response
