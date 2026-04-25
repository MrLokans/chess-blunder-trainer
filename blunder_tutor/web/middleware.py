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
from blunder_tutor.web.tls import is_https_request

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
    cache: dict[str, str] | None = getattr(request.app.state, "_locale_cache", None)
    if cache is None:
        cache = {}
        request.app.state._locale_cache = cache
    cache[key] = locale


MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# Paths that accept mutations from cross-origin contexts by design.
# Empty today — every state-changing endpoint is intended for same-origin
# UI use only. Keep the hook so adding e.g. a public webhook later
# doesn't require gutting the CSRF middleware.
CSRF_EXEMPT_PREFIXES: tuple[str, ...] = ()


class CsrfOriginMiddleware(BaseHTTPMiddleware):
    """Reject cross-origin state-changing requests.

    SameSite=Lax on the session cookie is the first line; ``Origin`` /
    ``Referer`` validation is the belt that catches the cases Lax misses
    (Firefox top-level POST navigations, legacy browsers, and the
    attacker-controlled top-level form that some UAs still ship with
    cookies attached). OWASP CSRF Cheat Sheet explicitly endorses the
    pattern as a stand-alone defense for stateful cookie auth when
    combined with SameSite.

    The middleware only inspects mutating methods. Safe methods (GET,
    HEAD, OPTIONS) are untouched.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in MUTATION_METHODS:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES):
            return await call_next(request)

        if not _origin_matches_host(request):
            return JSONResponse(
                {"error": "csrf", "message": "Origin header mismatch"},
                status_code=403,
            )
        return await call_next(request)


def _origin_matches_host(request: Request) -> bool:
    # Pick the first available source: Origin is set by modern browsers
    # on every POST; Referer is the fallback. If neither is present,
    # the request is either a non-browser client (CLI, programmatic)
    # or a browser with strict referrer policy — in both cases the
    # SameSite=Lax session cookie is the primary CSRF defense. Browser
    # CSRF requires cookies attached AND cross-origin initiation AND
    # headers set, so absent-both is not an exploitable attacker state.
    # This matches Django's default CSRF posture.
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    expected_host = _expected_host(request)

    if origin:
        return _extract_host(origin) == expected_host
    if referer:
        return _extract_host(referer) == expected_host
    return True


def _expected_host(request: Request) -> str | None:
    host = request.headers.get("host")
    if host is None:
        return None
    return host.split(":", 1)[0].lower()


def _extract_host(url: str) -> str | None:
    # "http://example.com:8000/path" → "example.com". We intentionally
    # don't use urllib.parse here: a carefully-crafted value with
    # embedded credentials or unicode could slip past a lazy parser.
    if "://" not in url:
        return None
    after_scheme = url.split("://", 1)[1]
    # Everything up to the first "/" or "?" is authority.
    for sep in ("/", "?", "#"):
        if sep in after_scheme:
            after_scheme = after_scheme.split(sep, 1)[0]
            break
    # Strip userinfo ("user:pass@host" — uncommon but legal).
    if "@" in after_scheme:
        after_scheme = after_scheme.rsplit("@", 1)[1]
    # Strip port.
    return after_scheme.split(":", 1)[0].lower()

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
            try:
                async with SettingsRepository(db_path=db_path) as settings_repo:
                    cache[key] = await settings_repo.is_setup_completed()
            except Exception:
                # DB initializing or missing — let the request through.
                return await call_next(request)

        if not cache[key]:
            return RedirectResponse(url="/setup", status_code=303)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers on every response.

    Scope deliberately conservative — no CSP yet because the Vite-built
    frontend mixes bundle loading with inline module scripts and a
    nonce-based CSP needs per-render nonce plumbing. Track CSP as a
    separate follow-up. What ships here is the non-CSP set:

    * ``X-Frame-Options: DENY`` — login page clickjacking defense, sibling
      routes aren't meant to be iframed either.
    * ``X-Content-Type-Options: nosniff`` — stops MIME-sniffing of JSON
      API responses into HTML contexts.
    * ``Referrer-Policy: strict-origin-when-cross-origin`` — the default
      several browsers use anyway, but pinning it removes surprise.
    * ``Strict-Transport-Security`` — only emitted when the request hits
      over HTTPS (direct or via trusted ``X-Forwarded-Proto``). An HSTS
      header on a plain-HTTP response poisons the browser HSTS cache for
      all future visits, so gate strictly.
    * ``Cache-Control: no-store`` on authenticated responses — prevents
      intermediary or shared-browser caches from serving one user's
      payload to another (OWASP Session Management 6.4).
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        auth_config = getattr(request.app.state, "auth_config", None)
        if auth_config is not None and is_https_request(request, auth_config):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        # no-store on any HTML render (keeps sensitive state off shared
        # browser caches) and on any authenticated JSON response
        # (intermediary caches on the path must not serve one user's
        # payload to another — OWASP Session Management 6.4).
        content_type = response.headers.get("content-type", "")
        ctx = getattr(request.state, "user_ctx", None)
        authenticated = ctx is not None and ctx.is_authenticated
        if "text/html" in content_type or authenticated:
            response.headers["Cache-Control"] = "no-store"
        return response


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        locale = await self._detect_locale(request)
        request.state.locale = locale

        i18n = getattr(request.app.state, "i18n", None)
        if i18n is not None:
            request.state.t = lambda key, **kwargs: i18n.t(locale, key, **kwargs)
            request.state.translations_json = json.dumps(
                i18n.get_all(locale), ensure_ascii=False
            )
        else:
            request.state.t = lambda key, **_: key
            request.state.translations_json = "{}"

        path = request.url.path
        if not path.startswith(("/static", "/api/", "/health", "/favicon")):
            features = await self._load_features(request)
        else:
            features = {f.value: v for f, v in DEFAULTS.items()}
        request.state.features = features
        request.state.features_json = json.dumps(features)

        # Cache-Control headers now live in SecurityHeadersMiddleware so
        # HTML + authed JSON share one policy.
        return await call_next(request)

    async def _load_features(self, request: Request) -> dict[str, bool]:
        db_path = _db_path_for(request)
        if db_path is None:
            return {f.value: v for f, v in DEFAULTS.items()}
        try:
            async with SettingsRepository(db_path=db_path) as settings_repo:
                return await settings_repo.get_feature_flags()
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
                async with SettingsRepository(db_path=db_path) as settings_repo:
                    db_locale = await settings_repo.get_setting("locale")
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
