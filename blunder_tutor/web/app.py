from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from functools import partial
from pathlib import Path

import chess.engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_throttle import RateLimiter
from starlette.middleware.trustedhost import TrustedHostMiddleware

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.auth import (
    CREDENTIALS_PROVIDER_NAME,
    INVITE_CODE_SETUP_KEY,
    AuthDb,
    AuthMiddleware,
    AuthService,
    BcryptHasher,
    CredentialsProvider,
    HmacInvitePolicy,
    MaxUsersQuota,
    MiddlewareConfig,
    SqliteStorage,
    UserId,
    UserRepo,
    ValidationRules,
    generate_invite_code,
    initialize_auth_schema,
    is_user_id_shape,
)
from blunder_tutor.background.executor import DbPathResolver, JobExecutor
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.cache import (
    CacheInvalidator,
    InMemoryCacheBackend,
    NullCacheBackend,
)
from blunder_tutor.cache.decorator import set_cache_backend
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.i18n import TranslationManager
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web import routes
from blunder_tutor.web.auth_hooks import (
    BlunderTutorFilePermissionPolicy,
    make_after_delete_hook,
    materialize_user_dir,
    resolve_user_db_path,
)
from blunder_tutor.web.bypass_auth import LOCAL_USER_ID, BypassAuthMiddleware
from blunder_tutor.web.config import AppConfig, config_factory
from blunder_tutor.web.cookies import SESSION_COOKIE_NAME
from blunder_tutor.web.middleware import (
    CsrfOriginMiddleware,
    DemoModeMiddleware,
    LocaleMiddleware,
    SecurityHeadersMiddleware,
    SetupCheckMiddleware,
    UserDbPathMiddleware,
)
from blunder_tutor.web.paths import AUTH_API_PREFIX, AUTH_UI_PATHS
from blunder_tutor.web.per_user_cache import PerUserCache
from blunder_tutor.web.resources import AuthResources
from blunder_tutor.web.template_context import i18n_context
from blunder_tutor.web.throttle import create_engine_throttle
from blunder_tutor.web.vite import vite_asset

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context manager for FastAPI app startup/shutdown."""

    # Startup: create work coordinator with engine pool
    coordinator: WorkCoordinator = app.state.work_coordinator
    await coordinator.start()

    # Auth bootstrap MUST run before the executor/scheduler start so the
    # AuthDb is available to the multi-user UserLister callback. The
    # locale-cache seed (none-mode only) and the WS broadcaster start
    # are independent and can run after.
    if app.state.auth_mode == "credentials":
        await _bootstrap_auth(app)

    settings_repo = app.state.settings_repo
    if settings_repo is not None:
        # None-mode only: single global SettingsRepository on the legacy
        # DB. Credentials mode resolves settings per-request, so this
        # warm-up is skipped and the locale cache starts empty.
        scheduler_settings = await settings_repo.get_all_settings()
        saved_locale = scheduler_settings.get("locale")
        if saved_locale:
            app.state.locale_cache.set(LOCAL_USER_ID, saved_locale)

    _wire_background(app)
    app.state.scheduler.start()

    # Subscribe BEFORE yield so callers publishing an event during
    # request handling never race the executor's queue subscription.
    await app.state.job_executor.subscribe()

    asyncio.create_task(app.state.connection_manager.start_broadcasting())
    asyncio.create_task(app.state.job_executor.run())
    asyncio.create_task(app.state.cache_invalidator.start())

    yield

    # Shutdown
    await app.state.cache_invalidator.stop()
    await app.state.job_executor.shutdown()
    app.state.scheduler.shutdown()
    await coordinator.shutdown()
    if settings_repo is not None:
        await settings_repo.close()
    # AuthDb owns the shared aiosqlite connection; close it here. Provider
    # lifecycles are currently no-ops (CredentialsProvider holds no external
    # resources) so AuthService has no close method — if a future provider
    # needs cleanup, re-add it and wire it back in the same spot. The
    # ``storage.auth_db`` escape hatch keeps the SQLite coupling visible.
    if app.state.auth is not None:
        await app.state.auth.storage.auth_db.close()


async def _bootstrap_auth(app: FastAPI) -> None:
    """Initialize `auth.sqlite3`, build the credentials-mode auth bundle,
    surface an invite code when no users exist, and run the orphan-directory
    scan. All side effects run on the app's own event loop so
    `aiosqlite` connections are bound to the same loop as request
    handlers.
    """
    config: AppConfig = app.state.config
    auth_config = config.auth
    auth_db_path = config.data.db_path.parent / "auth.sqlite3"
    users_dir = config.data.db_path.parent / "users"
    users_dir.mkdir(parents=True, exist_ok=True)

    await initialize_auth_schema(auth_db_path, BlunderTutorFilePermissionPolicy())

    auth_db = AuthDb(auth_db_path)
    await auth_db.connect()

    rules = ValidationRules.default()
    hasher = BcryptHasher(rules, cost=auth_config.bcrypt_cost)
    storage = SqliteStorage(auth_db)
    auth_service = AuthService(
        storage=storage,
        providers={
            CREDENTIALS_PROVIDER_NAME: CredentialsProvider(
                identities=storage.identities, hasher=hasher, rules=rules
            ),
        },
        hasher=hasher,
        quota=MaxUsersQuota(auth_config.max_users),
        invite_policy=HmacInvitePolicy(setup_repo=storage.setup),
        on_after_register=partial(materialize_user_dir, users_dir),
        on_after_delete=make_after_delete_hook(
            users_dir,
            app.state.setup_completed_cache,
            app.state.locale_cache,
            app.state.features_cache,
        ),
        session_max_age=timedelta(seconds=auth_config.session_max_age_seconds),
        session_idle=timedelta(seconds=auth_config.session_idle_seconds),
    )
    app.state.auth = AuthResources(
        storage=storage,
        service=auth_service,
        db_path=auth_db_path,
        users_dir=users_dir,
    )
    # Per-user DB path topology lives here, not in the auth core. The
    # `UserDbPathMiddleware` reads this resolver per-request to populate
    # `request.state.user_db_path`; `_wire_background` reuses it so the
    # foreground request path and background fan-out share one mapping.
    app.state.db_path_resolver = partial(resolve_user_db_path, users_dir)

    # Surface the most common insecure-default posture: credentials auth
    # but the operator has not indicated either HTTPS-direct or a trusted
    # reverse proxy. Without one of those, the session cookie ships
    # without `Secure` and is sniffable on any plaintext hop.
    if auth_config.cookie_secure is None and not auth_config.trust_proxy:
        log.warning(
            "AUTH_MODE=credentials is configured but neither "
            "AUTH_COOKIE_SECURE nor AUTH_TRUST_PROXY is set. Session "
            "cookies will drop the Secure flag on plain HTTP. Set "
            "AUTH_COOKIE_SECURE=true (HTTPS-direct) or AUTH_TRUST_PROXY"
            "=true + X-Forwarded-Proto in your reverse proxy."
        )

    if await auth_service.user_count() == 0:
        try:
            invite = await storage.setup.get(INVITE_CODE_SETUP_KEY)
            if invite is None:
                assert auth_config.secret_key is not None  # validated at boot
                invite = generate_invite_code(auth_config.secret_key)
                await storage.setup.put(INVITE_CODE_SETUP_KEY, invite)
            log.warning("=" * 60)
            log.warning("FIRST-USER SETUP: invite code required at /setup")
            log.warning("Invite code: %s", invite)
            log.warning("=" * 60)
        except Exception:
            # Non-fatal: a bad invite-code write shouldn't block the app
            # from booting. Operators can always re-bootstrap via the CLI
            # (Task 17).
            log.exception("Failed to generate or persist first-user invite code")

    await scan_orphans(storage.users, users_dir)


def _wire_background(app: FastAPI) -> None:
    """Build the JobExecutor + BackgroundScheduler with auth-mode-aware
    user enumeration. The per-user DB-path resolver is shared with the
    foreground request path via ``app.state.db_path_resolver``, set in
    ``create_app`` (none mode) or ``_bootstrap_auth`` (credentials mode).
    """
    config: AppConfig = app.state.config
    event_bus = app.state.event_bus
    work_coordinator = app.state.work_coordinator
    resolver: DbPathResolver = app.state.db_path_resolver

    if config.auth.mode == "credentials":
        assert app.state.auth is not None  # set by _bootstrap_auth
        users_repo = app.state.auth.storage.users

        async def list_users() -> list[UserId]:
            return [u.id for u in await users_repo.list_all()]

    else:

        async def list_users() -> list[UserId]:
            return [LOCAL_USER_ID]

    app.state.job_executor = JobExecutor(
        event_bus=event_bus,
        db_path_resolver=resolver,
        engine_path=config.engine_path,
        work_coordinator=work_coordinator,
    )
    app.state.scheduler = BackgroundScheduler(
        event_bus=event_bus,
        engine_path=config.engine_path,
        list_users=list_users,
        db_path_resolver=resolver,
    )


async def scan_orphans(users: UserRepo, users_dir: Path) -> None:
    """Log any per-user directories on disk that don't match a row in
    ``users``. Startup diagnostic only — deletion is the operator's
    call via the CLI (Task 17). A silent auto-delete would be a
    footgun: orphans can legitimately appear after a partial restore
    from backup, a botched manual ``rm``, or a crash mid-``delete_account``.

    Non-user-id-shaped entries (e.g. ``users/backups``, ``users/README``)
    are skipped — they're operator artefacts, not stale data.
    """
    if not users_dir.exists():
        return
    known = {u.id for u in await users.list_all()}
    for child in users_dir.iterdir():
        if child.is_dir() and is_user_id_shape(child.name) and child.name not in known:
            log.warning("Orphan user directory found (not deleted): %s", child)


def create_app(
    config: AppConfig,
) -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # Legacy single-user schema only applies to AUTH_MODE=none. In
    # credentials mode the legacy path is never opened and per-user DBs
    # are materialized on signup (Task 11).
    if config.auth.mode == "none":
        run_migrations(config.data.db_path)
        settings: SettingsRepository | None = SettingsRepository.from_config(
            config=config
        )
    else:
        settings = None

    templates = Jinja2Templates(
        directory=str(config.data.template_dir),
        context_processors=[i18n_context],
    )

    # Initialize i18n
    locales_dir = Path(__file__).parent.parent.parent / "locales"
    i18n = TranslationManager(locales_dir)
    app.state.i18n = i18n

    # Per-request template state (t, locale, features, translations_json,
    # features_json) is plumbed via ``i18n_context`` from ``request.state``
    # so concurrent renders can't observe each other's context. See
    # ``template_context.py`` for the processor and the LocaleMiddleware
    # for where the request state is populated.
    templates.env.globals["available_locales"] = i18n.available_locales
    templates.env.globals["vite_asset"] = lambda entry: vite_asset(
        entry, dev_mode=config.vite_dev
    )

    limit = (
        chess.engine.Limit(time=config.engine.time_limit)
        if config.engine.time_limit is not None
        else chess.engine.Limit(depth=config.engine.depth)
    )
    app.state.config = config
    app.state.templates = templates
    app.state.limit = limit

    # Initialize work coordinator (engine pool + task queue)
    work_coordinator = WorkCoordinator(engine_path=config.engine_path)
    app.state.work_coordinator = work_coordinator

    # Initialize event bus and WebSocket manager
    event_bus = EventBus()
    app.state.event_bus = event_bus

    if config.cache.enabled:
        cache_backend = InMemoryCacheBackend()
    else:
        cache_backend = NullCacheBackend()
    app.state.cache = cache_backend
    set_cache_backend(cache_backend, default_ttl=config.cache.default_ttl)

    cache_invalidator = CacheInvalidator(cache=cache_backend, event_bus=event_bus)
    app.state.cache_invalidator = cache_invalidator

    connection_manager = ConnectionManager(event_bus)
    app.state.connection_manager = connection_manager

    # JobExecutor + BackgroundScheduler are constructed in the lifespan
    # by `_wire_background` once auth bootstrap has populated the AuthDb
    # (credentials mode needs the user list at tick time).
    app.state.job_executor = None
    app.state.scheduler = None
    app.state.settings_repo = settings

    # Auth state. `app.state.auth` is the credentials-mode bundle
    # (AuthDb + AuthService + paths) materialized in `_bootstrap_auth`;
    # readers narrow on `if app.state.auth is not None` so the type
    # system carries the mode invariant.
    # `none_mode_db_path` is the legacy single-user DB path. It is set
    # ONLY when ``auth.mode == "none"`` so any code that reaches for
    # ``app.state.none_mode_db_path`` in credentials mode raises
    # AttributeError instead of silently writing to the wrong DB. The
    # ``tests/test_none_mode_db_path_isolation.py`` structural guard
    # enforces that only the documented call sites read this attribute.
    app.state.auth_mode = config.auth.mode
    app.state.auth_config = config.auth
    # Set to AuthResources by `_bootstrap_auth` lifespan in credentials mode.
    app.state.auth = None

    if config.auth.mode == "none":
        app.state.none_mode_db_path = config.data.db_path
        # Single-user topology: every request resolves to the same legacy
        # DB. Credentials mode populates this in `_bootstrap_auth` once
        # `users_dir` is known.
        none_db_path = config.data.db_path
        app.state.db_path_resolver = lambda _user_id: none_db_path

    # Per-user caches keyed on user_id (or `_local` in none-mode). Always
    # present so middleware never has to lazy-init; `PerUserCache` is the
    # only API for touching them — see `blunder_tutor/web/per_user_cache.py`.
    # Populated as a side effect of `get_settings_snapshot` (the single
    # per-request DB-open seam) and invalidated by the settings/auth
    # mutations that change them.
    app.state.setup_completed_cache = PerUserCache[bool]()
    app.state.locale_cache = PerUserCache[str]()
    app.state.features_cache = PerUserCache[dict[str, bool]]()

    # Mount static files directory
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Inject demo_mode flag into app state and templates
    app.state.demo_mode = config.demo_mode
    templates.env.globals["demo_mode"] = config.demo_mode

    # Inject analytics config into templates
    templates.env.globals["analytics_enabled"] = config.analytics.enabled
    templates.env.globals["plausible_domain"] = config.analytics.plausible_domain
    templates.env.globals["plausible_script_url"] = (
        config.analytics.plausible_script_url
    )

    # Set up per-IP engine throttle for demo mode
    app.state.engine_throttle = create_engine_throttle(config)

    # Per-IP rate limiters for auth endpoints. `RateLimiter` is stateful
    # (in-memory sliding-window), so it must be instantiated once per
    # process and reused across requests — re-instantiating per-request
    # would give every attempt a fresh bucket and defeat the limiter.
    # ``trust_proxy`` is opt-in via `AUTH_TRUST_PROXY`: default ``False``
    # keys the limiter on the direct client IP, so a direct-to-uvicorn
    # deploy cannot be bypassed by spoofing ``X-Forwarded-For``. Flip
    # to ``True`` only behind a reverse proxy that overwrites the
    # header.
    app.state.login_rate_limiter = RateLimiter(
        times=config.auth.login_rate_limit,
        seconds=config.auth.login_rate_window_seconds,
        trust_proxy=config.auth.trust_proxy,
        add_headers=True,
        detail="Too many login attempts; please wait and try again.",
    )
    app.state.signup_rate_limiter = RateLimiter(
        times=config.auth.signup_rate_limit,
        seconds=config.auth.signup_rate_window_seconds,
        trust_proxy=config.auth.trust_proxy,
        add_headers=True,
        detail="Too many signup attempts; please wait and try again.",
    )

    # Add middleware (order matters: last added = first executed).
    # `AuthMiddleware` runs first so downstream middleware can read the
    # per-request `user_ctx` / `db_path` from `request.state`.
    # `SecurityHeadersMiddleware` is added first (runs last on response)
    # so it stamps headers regardless of what earlier middleware returned
    # — including Auth's 401 and redirect responses.
    # Host header allowlist. Without it, a shared-vhost deployment lets
    # any cross-origin attacker pass the CSRF Origin/Host equality check
    # by sending a spoofed Host header. When `allowed_hosts` is set,
    # Starlette TrustedHostMiddleware returns 400 for any mismatch
    # BEFORE other middleware sees the request. Default "*" preserves
    # behavior for single-host dev setups; operators MUST configure
    # this on any multi-tenant or shared-origin deploy.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.allowed_hosts))
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SetupCheckMiddleware)
    app.add_middleware(DemoModeMiddleware)
    app.add_middleware(LocaleMiddleware)
    # `UserDbPathMiddleware` must run AFTER `AuthMiddleware` (which sets
    # `request.state.user_ctx`) and BEFORE the middleware that opens
    # per-user DBs (`SetupCheckMiddleware`, `LocaleMiddleware`). Add
    # order is reverse of execution: added BEFORE Auth here so it runs
    # AFTER it on the request.
    app.add_middleware(UserDbPathMiddleware)
    # AuthMiddleware (credentials mode) and BypassAuthMiddleware (none
    # mode) are mutually exclusive: each writes the same `user_ctx`
    # request-state slot, so registering both would have the inner one
    # silently overwrite the outer's value. The auth core knows nothing
    # about none mode after TREK-54 — that branch lives entirely here.
    # Any future mode that synthesises a `user_ctx` (e.g. a header-token
    # bypass for an internal service) belongs to this same if/elif.
    if config.auth.mode == "credentials":
        app.add_middleware(
            AuthMiddleware,
            config=MiddlewareConfig(
                cookie_name=SESSION_COOKIE_NAME,
                exempt_paths=AUTH_UI_PATHS | {"/health", "/favicon.ico"},
                exempt_prefixes=("/static", AUTH_API_PREFIX),
            ),
        )
    else:
        app.add_middleware(BypassAuthMiddleware)
    # CsrfOriginMiddleware added LAST → runs FIRST on the request path.
    # A cross-origin mutation must be rejected before Auth/Locale/Setup
    # run any side effects (DB lookups, cache writes). AuthMiddleware's
    # /login redirect would otherwise consume the request before CSRF
    # sees it, violating the "CSRF rejects before side effects" invariant.
    app.add_middleware(CsrfOriginMiddleware)
    app = routes.configure_router(app)
    return app


def create_app_factory() -> FastAPI:
    """Factory function for uvicorn --factory mode."""
    return create_app(config_factory(None, os.environ))
