from __future__ import annotations

import json
import re

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.features import DEFAULTS
from blunder_tutor.repositories.settings import SettingsRepository

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
    EXEMPT_PATHS = {"/setup", "/api/", "/health", "/static", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        if getattr(request.app.state, "demo_mode", False):
            return await call_next(request)

        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            return await call_next(request)

        # Check if setup is completed (with caching to reduce DB load)
        if not hasattr(request.app.state, "_setup_completed_cache"):
            config = request.app.state.config
            settings_repo = SettingsRepository(db_path=config.data.db_path)
            try:
                request.app.state._setup_completed_cache = (
                    await settings_repo.is_setup_completed()
                )
            except Exception:
                # If we can't check setup status, allow the request through
                # (database might be initializing)
                return await call_next(request)

        if not request.app.state._setup_completed_cache:
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
        try:
            config = request.app.state.config
            settings_repo = SettingsRepository(db_path=config.data.db_path)
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

        cached = getattr(request.app.state, "_locale_cache", None)
        if cached:
            return cached

        try:
            config = request.app.state.config
            settings_repo = SettingsRepository(db_path=config.data.db_path)
            try:
                db_locale = await settings_repo.get_setting("locale")
            finally:
                await settings_repo.close()
            if db_locale and i18n and db_locale in i18n.available_locales():
                request.app.state._locale_cache = db_locale
                return db_locale
        except Exception:
            pass

        accept = request.headers.get("accept-language", "")
        for part in accept.split(","):
            lang = part.split(";")[0].strip().split("-")[0].lower()
            if i18n and lang in i18n.available_locales():
                return lang

        return "en"
