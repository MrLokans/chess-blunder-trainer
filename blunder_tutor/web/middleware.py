from __future__ import annotations

import json
import re

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from blunder_tutor.features import DEFAULTS
from blunder_tutor.web.paths import AUTH_API_PREFIX, AUTH_UI_PATHS
from blunder_tutor.web.request_helpers import _cache_key, _db_path_for
from blunder_tutor.web.settings_snapshot import get_settings_snapshot
from blunder_tutor.web.tls import is_https_request

# Re-exported so existing call sites (`web/api/settings.py`, tests)
# don't need to update their imports. The canonical home is
# `web/request_helpers.py` — that's where settings_snapshot.py imports
# from to break what would otherwise be a circular import via this
# module.
__all__ = ["_cache_key", "_db_path_for"]


class UserDbPathMiddleware(BaseHTTPMiddleware):
    """Map the per-request :class:`UserContext` to a per-user DB path
    via the resolver stored on ``app.state.db_path_resolver``.

    Sits above :class:`AuthMiddleware` in the request chain (added
    *before* it so it runs *after* on the way in) and below the rest of
    the web-layer middleware that needs to open a per-user DB
    (`SetupCheckMiddleware`, `LocaleMiddleware`, route handlers via
    `get_db_path`).

    The auth core (``blunder_tutor/auth/``) deliberately knows nothing
    about filesystem topology: a future shared-DB SaaS port swaps the
    resolver for one that returns the same path for every user, and a
    multi-tenant port swaps it for a tenant-id resolver — neither
    requires touching :class:`UserContext`.

    When ``request.state.user_ctx`` is ``None`` (credentials mode pre-
    auth on an exempt path, e.g. ``/login``), no path is set and
    :func:`_db_path_for` returns ``None`` — callers fall back to
    defaults instead of opening an un-migrated DB.
    """

    async def dispatch(self, request: Request, call_next):
        ctx = getattr(request.state, "user_ctx", None)
        if ctx is not None:
            resolver = request.app.state.db_path_resolver
            request.state.user_db_path = resolver(ctx.user_id)
        return await call_next(request)


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

        cache = request.app.state.setup_completed_cache
        key = _cache_key(request)
        completed = cache.get(key)
        if completed is None:
            # `get_settings_snapshot` warms setup_completed_cache /
            # locale_cache / features_cache as a side effect — keep the
            # cache check above so a warm path skips the DB open entirely.
            snapshot = await get_settings_snapshot(request)
            completed = snapshot.setup_completed
            if completed is None:
                # DB unavailable (credentials mode pre-auth, or DB
                # initializing) — let the request through; downstream
                # auth/route logic decides what to do.
                return await call_next(request)

        if not completed:
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
        # Cache check first; snapshot warms features_cache as a side
        # effect, so a warm path never opens the DB.
        cache = request.app.state.features_cache
        key = _cache_key(request)
        cached = cache.get(key)
        if cached is not None:
            return cached
        snapshot = await get_settings_snapshot(request)
        if snapshot.features is None:
            return {f.value: v for f, v in DEFAULTS.items()}
        return snapshot.features

    async def _detect_locale(self, request: Request) -> str:
        i18n = getattr(request.app.state, "i18n", None)

        cookie_locale = request.cookies.get("locale")
        if cookie_locale and i18n and cookie_locale in i18n.available_locales():
            return cookie_locale

        key = _cache_key(request)
        cached = request.app.state.locale_cache.get(key)
        if cached is not None:
            return cached

        snapshot = await get_settings_snapshot(request)
        db_locale = snapshot.locale
        if db_locale and i18n and db_locale in i18n.available_locales():
            return db_locale

        accept = request.headers.get("accept-language", "")
        for part in accept.split(","):
            lang = part.split(";")[0].strip().split("-")[0].lower()
            if i18n and lang in i18n.available_locales():
                return lang

        return "en"
