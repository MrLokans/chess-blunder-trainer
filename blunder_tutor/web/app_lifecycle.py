from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from contextlib import asynccontextmanager, suppress
from datetime import timedelta
from functools import partial
from pathlib import Path
from typing import Any

import chess.engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_throttle import RateLimiter
from starlette.middleware.trustedhost import TrustedHostMiddleware

from blunder_tutor import auth as auth_pkg
from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.auth.fastapi import SESSION_COOKIE_NAME
from blunder_tutor.background.executor import DbPathResolver, JobExecutor
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.cache.backend import InMemoryCacheBackend, NullCacheBackend
from blunder_tutor.cache.invalidation import CacheInvalidator
from blunder_tutor.constants import AUTH_MODE_CREDENTIALS, AUTH_MODE_NONE
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.i18n.manager import TranslationManager
from blunder_tutor.migrations import run_migrations
from blunder_tutor.observability import init_observability, shutdown_observability
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web import routes
from blunder_tutor.web.auth_hooks import (
    BlunderTutorFilePermissionPolicy,
    make_after_delete_hook,
    materialize_user_dir,
    resolve_user_db_path,
)
from blunder_tutor.web.bypass_auth import LOCAL_USER_ID, BypassAuthMiddleware
from blunder_tutor.web.config import AppConfig
from blunder_tutor.web.host_policy import LocalHostOnlyMiddleware
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


async def _list_users_none_mode() -> list[auth_pkg.UserId]:
    return [LOCAL_USER_ID]


async def _list_users_credentials_mode(users_repo) -> list[auth_pkg.UserId]:  # type: ignore[no-untyped-def]
    return [u.id for u in await users_repo.list_all()]


def _build_auth_service(
    storage: auth_pkg.SqliteStorage,
    rules: auth_pkg.ValidationRules,
    auth_config,
    users_dir: Path,
    app: FastAPI,
) -> auth_pkg.AuthService:
    hasher = auth_pkg.BcryptHasher(rules, cost=auth_config.bcrypt_cost)
    return auth_pkg.AuthService(
        storage=storage,
        providers={
            auth_pkg.CREDENTIALS_PROVIDER_NAME: auth_pkg.CredentialsProvider(
                identities=storage.identities, hasher=hasher, rules=rules
            ),
        },
        hasher=hasher,
        quota=auth_pkg.MaxUsersQuota(auth_config.max_users),
        invite_policy=auth_pkg.HmacInvitePolicy(setup_repo=storage.setup),
        session_config=auth_pkg.SessionConfig(
            max_age=timedelta(seconds=auth_config.session_max_age_seconds),
            idle=timedelta(seconds=auth_config.session_idle_seconds),
        ),
        on_after_register=partial(materialize_user_dir, users_dir),
        on_after_delete=make_after_delete_hook(
            users_dir,
            app.state.setup_completed_cache,
            app.state.locale_cache,
            app.state.features_cache,
        ),
    )


async def _handle_first_user_invite(
    storage: auth_pkg.SqliteStorage, secret_key: str | None
) -> None:
    try:
        invite = await storage.setup.get(auth_pkg.INVITE_CODE_SETUP_KEY)
        if invite is None:
            assert secret_key is not None  # validated at boot
            invite = auth_pkg.generate_invite_code(secret_key)
            await storage.setup.put(auth_pkg.INVITE_CODE_SETUP_KEY, invite)
    except Exception:
        # Non-fatal: a bad invite-code write shouldn't block the app
        # from booting. Operators can always re-bootstrap via the CLI.
        log.exception("Failed to generate or persist first-user invite code")
        return
    log.warning("=" * 60)
    log.warning("FIRST-USER SETUP: invite code required at /setup")
    log.warning("Invite code: %s", invite)
    log.warning("=" * 60)


def _warn_insecure_cookie_posture(auth_config) -> None:
    if auth_config.cookie_secure is None and not auth_config.trust_proxy:
        log.warning(
            "AUTH_MODE=credentials is configured but neither "
            "AUTH_COOKIE_SECURE nor AUTH_TRUST_PROXY is set. Session "
            "cookies will drop the Secure flag on plain HTTP. Set "
            "AUTH_COOKIE_SECURE=true (HTTPS-direct) or AUTH_TRUST_PROXY"
            "=true + X-Forwarded-Proto in your reverse proxy."
        )


async def _bootstrap_auth(app: FastAPI) -> None:
    """Runs on the app's event loop so aiosqlite connections match the request handlers'
    loop."""
    config: AppConfig = app.state.config
    auth_config = config.auth
    auth_db_path = config.data.db_path.parent / "auth.sqlite3"
    users_dir = config.data.db_path.parent / "users"
    users_dir.mkdir(parents=True, exist_ok=True)

    await auth_pkg.initialize_auth_schema(
        auth_db_path, BlunderTutorFilePermissionPolicy()
    )

    auth_db = auth_pkg.AuthDb(auth_db_path)
    await auth_db.connect()

    rules = auth_pkg.ValidationRules.default()
    storage = auth_pkg.SqliteStorage(auth_db)
    auth_service = _build_auth_service(storage, rules, auth_config, users_dir, app)

    app.state.auth = AuthResources(
        storage=storage,
        service=auth_service,
        db_path=auth_db_path,
        users_dir=users_dir,
    )
    # Per-user DB topology lives here, not in the auth core; `UserDbPathMiddleware` and
    # `_wire_background` share this one mapping.
    app.state.db_path_resolver = partial(resolve_user_db_path, users_dir)

    _warn_insecure_cookie_posture(auth_config)

    if await auth_service.user_count() == 0:
        await _handle_first_user_invite(storage, auth_config.secret_key)

    await scan_orphans(storage.users, users_dir)


def _wire_background(app: FastAPI) -> None:
    config: AppConfig = app.state.config
    event_bus = app.state.event_bus
    work_coordinator = app.state.work_coordinator
    resolver: DbPathResolver = app.state.db_path_resolver

    if config.auth.mode == AUTH_MODE_CREDENTIALS:
        assert app.state.auth is not None  # set by _bootstrap_auth
        list_users = partial(_list_users_credentials_mode, app.state.auth.storage.users)
    else:
        list_users = _list_users_none_mode

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


async def scan_orphans(users: auth_pkg.UserRepo, users_dir: Path) -> None:
    """Diagnostic only: deletion is the operator's call, since orphans appear after partial
    restores or crashes mid-delete."""
    if not users_dir.exists():
        return
    known = {u.id for u in await users.list_all()}
    for child in users_dir.iterdir():
        if (
            child.is_dir()
            and auth_pkg.is_user_id_shape(child.name)
            and child.name not in known
        ):
            log.warning("Orphan user directory found (not deleted): %s", child)


async def _seed_locale_cache(app: FastAPI) -> None:
    settings_repo = app.state.settings_repo
    if settings_repo is None:
        return
    # None-mode only: single global SettingsRepository on the legacy DB.
    # Credentials mode resolves settings per-request, so this warm-up is
    # skipped and the locale cache starts empty.
    scheduler_settings = await settings_repo.get_all_settings()
    saved_locale = scheduler_settings.get("locale")
    if saved_locale:
        app.state.locale_cache.set(LOCAL_USER_ID, saved_locale)


def _on_supervised_exit(name: str, task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        log.error("Supervised task %r crashed", name, exc_info=exc)
    else:
        log.error(
            "Supervised task %r exited unexpectedly; it must run for the "
            "process lifetime",
            name,
        )


def _supervise(name: str, coro: Coroutine[Any, Any, None]) -> asyncio.Task:
    # A fire-and-forget task's crash is invisible until GC, which never happens for a
    # process-lifetime task; the done-callback logs it. `job_executor.run()` has the
    # same issue (separate ticket).
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(partial(_on_supervised_exit, name))
    return task


async def _run_startup(app: FastAPI) -> None:
    # First, so any later startup exception is captured by Sentry.
    config: AppConfig = app.state.config
    init_observability(config.observability)

    coordinator: WorkCoordinator = app.state.work_coordinator
    await coordinator.start()

    # Must precede executor/scheduler: the multi-user `UserLister` needs the AuthDb.
    if app.state.auth_mode == AUTH_MODE_CREDENTIALS:
        await _bootstrap_auth(app)

    await _seed_locale_cache(app)

    _wire_background(app)
    app.state.scheduler.start()

    # Subscribe before yield so events published during requests don't race the
    # subscription.
    await app.state.job_executor.subscribe()

    app.state.broadcast_task = _supervise(
        "ws-broadcast", app.state.connection_manager.start_broadcasting()
    )
    asyncio.create_task(app.state.job_executor.run())
    await app.state.cache_invalidator.start()


async def _close_storage(app: FastAPI) -> None:
    settings_repo = app.state.settings_repo
    if settings_repo is not None:
        await settings_repo.close()
    # AuthDb owns the shared connection. Providers hold no resources, so `AuthService`
    # has no close.
    if app.state.auth is not None:
        auth_db = app.state.auth.storage.auth_db
        await auth_db.close()


async def _run_cleanup(app: FastAPI) -> None:
    # Cancelling runs the broadcaster's finally, which closes the coalescer;
    # `_on_supervised_exit` stays silent on cancel.
    broadcast_task = app.state.broadcast_task
    broadcast_task.cancel()
    with suppress(asyncio.CancelledError):
        await broadcast_task
    await app.state.cache_invalidator.stop()
    await app.state.job_executor.shutdown()
    app.state.scheduler.shutdown()
    coordinator: WorkCoordinator = app.state.work_coordinator
    await coordinator.shutdown()
    await _close_storage(app)


async def _run_shutdown(app: FastAPI) -> None:
    try:  # noqa: WPS501 — bare try/finally is intentional: re-raise the original cleanup failure but still flush Sentry.
        await _run_cleanup(app)
    finally:
        # In `finally` so a failure in earlier cleanup still flushes buffered events;
        # the flush has its own 2s timeout.
        shutdown_observability()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _run_startup(app)
    yield
    await _run_shutdown(app)


def _init_templates(app: FastAPI, config: AppConfig) -> Jinja2Templates:
    templates = Jinja2Templates(
        directory=str(config.data.template_dir),
        context_processors=[i18n_context],
    )
    locales_dir = Path(__file__).parent.parent.parent / "locales"
    i18n = TranslationManager(locales_dir)
    app.state.i18n = i18n

    templates.env.globals["available_locales"] = i18n.available_locales
    templates.env.globals["vite_asset"] = lambda entry: vite_asset(
        entry, dev_mode=config.vite_dev
    )
    templates.env.globals["demo_mode"] = config.demo_mode
    templates.env.globals["analytics_enabled"] = config.analytics.enabled
    templates.env.globals["plausible_domain"] = config.analytics.plausible_domain
    templates.env.globals["plausible_script_url"] = (
        config.analytics.plausible_script_url
    )

    return templates


def _engine_limit(config: AppConfig) -> chess.engine.Limit:
    if config.engine.time_limit is not None:
        return chess.engine.Limit(time=config.engine.time_limit)
    return chess.engine.Limit(depth=config.engine.depth)


def _init_caches(app: FastAPI, config: AppConfig) -> None:
    cache_backend = (
        InMemoryCacheBackend() if config.cache.enabled else NullCacheBackend()
    )
    app.state.cache = cache_backend
    app.state.cache_invalidator = CacheInvalidator(
        cache=cache_backend, event_bus=app.state.event_bus
    )

    # Always present so middleware never lazy-inits.
    app.state.setup_completed_cache = PerUserCache[bool]()
    app.state.locale_cache = PerUserCache[str]()
    app.state.features_cache = PerUserCache[dict[str, bool]]()


def _init_rate_limiters(app: FastAPI, config: AppConfig) -> None:
    # RateLimiter is stateful (in-memory window): one instance per process.
    # `trust_proxy` defaults False so a spoofed `X-Forwarded-For` can't bypass it;
    # enable only behind a proxy that overwrites the header.
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


def _init_state(app: FastAPI, config: AppConfig) -> None:
    if config.auth.mode == AUTH_MODE_NONE:
        run_migrations(config.data.db_path)
        settings = SettingsRepository.from_config(config=config)
    else:
        settings = None

    app.state.config = config
    app.state.limit = _engine_limit(config)
    app.state.work_coordinator = WorkCoordinator(engine_path=config.engine_path)
    app.state.event_bus = EventBus()
    _init_caches(app, config)
    app.state.connection_manager = ConnectionManager(app.state.event_bus)

    app.state.job_executor = None
    app.state.scheduler = None
    app.state.settings_repo = settings

    # `none_mode_db_path` is set only when `auth.mode == "none"`, so reads in
    # credentials mode raise AttributeError rather than silently hit the wrong DB;
    # `tests/test_none_mode_db_path_isolation.py` guards the call sites.
    app.state.auth_mode = config.auth.mode
    app.state.auth_config = config.auth
    app.state.auth = None

    if config.auth.mode == AUTH_MODE_NONE:
        app.state.none_mode_db_path = config.data.db_path
        # Single-user topology: every request resolves to the legacy DB.
        none_db_path = config.data.db_path
        app.state.db_path_resolver = lambda _user_id: none_db_path

    app.state.demo_mode = config.demo_mode
    app.state.engine_throttle = create_engine_throttle(config)
    _init_rate_limiters(app, config)


def _register_middleware(app: FastAPI, config: AppConfig) -> None:
    # Middleware runs in reverse add order. `SecurityHeadersMiddleware` is added first
    # so it stamps headers on every response, including Auth's 401/redirects.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SetupCheckMiddleware)
    app.add_middleware(DemoModeMiddleware)
    app.add_middleware(LocaleMiddleware)
    # Must run after `AuthMiddleware` (sets `user_ctx`) and before middleware that opens
    # per-user DBs; added before Auth, so it executes after.
    app.add_middleware(UserDbPathMiddleware)
    # Auth and Bypass middleware are mutually exclusive: both write `user_ctx`, so the
    # inner would overwrite the outer.
    if config.auth.mode == AUTH_MODE_CREDENTIALS:
        app.add_middleware(
            auth_pkg.AuthMiddleware,
            config=auth_pkg.MiddlewareConfig(
                cookie_name=SESSION_COOKIE_NAME,
                exempt_paths=AUTH_UI_PATHS | {"/health", "/favicon.ico"},
                exempt_prefixes=("/static", AUTH_API_PREFIX),
            ),
        )
    else:
        app.add_middleware(BypassAuthMiddleware)
    # Added late so CSRF runs before Auth: a cross-origin mutation must be rejected
    # before Auth's /login redirect or any other side effect.
    app.add_middleware(CsrfOriginMiddleware)
    # Added last so the Host allowlist runs first: without it, a shared-vhost deploy
    # lets a cross-origin attacker pass the CSRF Origin/Host check with a spoofed Host,
    # and a no-login instance is open to DNS rebinding.
    if config.allowed_hosts is not None:
        app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=list(config.allowed_hosts)
        )
    elif config.auth.mode == AUTH_MODE_NONE and not config.demo_mode:
        app.add_middleware(LocalHostOnlyMiddleware)


def build_app(config: AppConfig) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    _init_state(app, config)
    templates = _init_templates(app, config)
    app.state.templates = templates

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    _register_middleware(app, config)
    return routes.configure_router(app)
