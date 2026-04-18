from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.features import DEFAULTS
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web.paths import AUTH_API_PREFIX, AUTH_UI_PATHS

# App-level per-user cache key for pre-auth / AUTH_MODE=none requests. The
# sentinel matches the `_local` UserContext that AuthMiddleware synthesises
# in none mode, so the two modes share a single keying strategy.
_NONE_MODE_CACHE_KEY = "_local"


def _cache_key(request: Request) -> str:
    """Per-user cache key. Preserves none-mode semantics (one key for the
    single legacy user) and isolates credentials-mode users from each
    other so setup/locale/feature caches do not leak across accounts.
    """
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        return ctx.user_id
    return _NONE_MODE_CACHE_KEY


def _db_path_for(request: Request) -> Path | None:
    """Return the per-request DB path: the signed-in user's DB when an
    `AuthMiddleware`-populated context is present, otherwise the legacy
    single-user path (AUTH_MODE=none).

    In credentials mode with no context (exempt paths before any user is
    signed in) there is no legitimate DB to hit — return ``None`` and let
    the caller fall back to defaults instead of silently opening the
    un-migrated legacy ``data/main.sqlite3``.
    """
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        return ctx.db_path
    if getattr(request.app.state, "auth_mode", "none") == "credentials":
        return None
    return request.app.state.config.data.db_path


def invalidate_setup_cache(request: Request, key: str) -> None:
    cache: dict[str, bool] | None = getattr(
        request.app.state, "_setup_completed_cache", None
    )
    if cache is not None:
        cache.pop(key, None)


def set_locale_cache(request: Request, key: str, locale: str) -> None:
    cache: dict[str, str] | None = getattr(
        request.app.state, "_locale_cache", None
    )
    if cache is None:
        cache = {}
        request.app.state._locale_cache = cache
    cache[key] = locale


MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

DEMO_ALLOWED_MUTATIONS: list[tuple[str, re.Pattern]] = [
    ("POST", re.compile(r"^/api/submit$")),
    ("POST", re.compile(r"^/api/analyze$")),
    ("POST", re.compile(r"^/api/settings/locale$")),
    ("POST", re.compile(r"^/api/validate-username$")),
]


class DemoModeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not getattr(request.app.state, "demo_mode", False):
            return await call_next(request)

        method = request.method
        path = request.url.path

        if method in MUTATION_METHODS:
            for m, pattern in DEMO_ALLOWED_MUTATIONS:
                if method == m and pattern.search(path):
                    return await call_next(request)

            return JSONResponse(
                status_code=403,
                content={
                    "error": "demo_mode",
                    "message": "This action is disabled in demo mode",
                },
            )

        return await call_next(request)


LOCALE_DISPLAY_NAMES = {
    "en": "English",
    "ru": "Русский",
    "uk": "Українська",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pl": "Polski",
    "be": "Беларуская",
    "zh": "中文",
}


class SetupCheckMiddleware(BaseHTTPMiddleware):
    # `SetupCheckMiddleware` matches via ``startswith``, so `/api/` here
    # covers every API surface (not just `/api/auth/`). We still list
    # `AUTH_API_PREFIX` explicitly so a future refactor that tightens the
    # `/api/` guard doesn't accidentally trap the auth API behind setup.
    EXEMPT_PATHS = AUTH_UI_PATHS | frozenset(
        {"/api/", "/health", "/static", "/favicon.ico", AUTH_API_PREFIX}
    )

    async def dispatch(self, request: Request, call_next):
        if getattr(request.app.state, "demo_mode", False):
            return await call_next(request)

        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)

        db_path = _db_path_for(request)
        if db_path is None:
            # Credentials mode without a user context: the only requests
            # reaching here are exempt-path misses, and we have no DB to
            # consult. Fall through — the route will handle auth itself.
            return await call_next(request)

        cache: dict[str, bool] | None = getattr(
            request.app.state, "_setup_completed_cache", None
        )
        if cache is None:
            cache = {}
            request.app.state._setup_completed_cache = cache

        key = _cache_key(request)
        if key not in cache:
            settings_repo = SettingsRepository(db_path=db_path)
            try:
                cache[key] = await settings_repo.is_setup_completed()
            except Exception:
                # DB initializing or missing — let the request through.
                return await call_next(request)
            finally:
                await settings_repo.close()

        if not cache[key]:
            return RedirectResponse(url="/setup", status_code=303)

        return await call_next(request)


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        locale = await self._detect_locale(request)
        request.state.locale = locale

        i18n = getattr(request.app.state, "i18n", None)
        if i18n:
            templates = request.app.state.templates
            translations = i18n.get_all(locale)
            templates.env.globals["t"] = lambda key, **kwargs: i18n.t(
                locale, key, **kwargs
            )
            templates.env.globals["locale"] = locale
            templates.env.globals["translations_json"] = json.dumps(
                translations, ensure_ascii=False
            )
            templates.env.globals["locale_display_names"] = LOCALE_DISPLAY_NAMES

        path = request.url.path
        if not path.startswith(("/static", "/api/", "/health", "/favicon")):
            features = await self._load_features(request)
            request.app.state.templates.env.globals["features"] = features
            request.app.state.templates.env.globals["has_feature"] = features.get
            request.app.state.templates.env.globals["features_json"] = json.dumps(
                features
            )

        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-store"

        return response

    async def _load_features(self, request: Request) -> dict[str, bool]:
        db_path = _db_path_for(request)
        if db_path is None:
            return {f.value: v for f, v in DEFAULTS.items()}
        try:
            settings_repo = SettingsRepository(db_path=db_path)
            try:
                return await settings_repo.get_feature_flags()
            finally:
                await settings_repo.close()
        except Exception:
            return {f.value: v for f, v in DEFAULTS.items()}

    async def _detect_locale(self, request: Request) -> str:
        i18n = getattr(request.app.state, "i18n", None)

        cookie_locale = request.cookies.get("locale")
        if cookie_locale and i18n and cookie_locale in i18n.available_locales():
            return cookie_locale

        locale_cache: dict[str, str] | None = getattr(
            request.app.state, "_locale_cache", None
        )
        key = _cache_key(request)
        if locale_cache is not None and key in locale_cache:
            return locale_cache[key]

        db_path = _db_path_for(request)
        if db_path is not None:
            try:
                settings_repo = SettingsRepository(db_path=db_path)
                try:
                    db_locale = await settings_repo.get_setting("locale")
                finally:
                    await settings_repo.close()
                if db_locale and i18n and db_locale in i18n.available_locales():
                    set_locale_cache(request, key, db_locale)
                    return db_locale
            except Exception:
                pass

        accept = request.headers.get("accept-language", "")
        for part in accept.split(","):
            lang = part.split(";")[0].strip().split("-")[0].lower()
            if i18n and lang in i18n.available_locales():
                return lang

        return "en"
