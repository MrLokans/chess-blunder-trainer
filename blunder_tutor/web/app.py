from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import chess.engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.auth.db import AuthDb
from blunder_tutor.auth.invite import generate_invite_code
from blunder_tutor.auth.middleware import AuthMiddleware
from blunder_tutor.auth.repository import SetupRepository
from blunder_tutor.auth.schema import initialize_auth_schema
from blunder_tutor.auth.service import AuthService
from blunder_tutor.background.executor import JobExecutor
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
from blunder_tutor.web.config import AppConfig, config_factory
from blunder_tutor.web.middleware import (
    DemoModeMiddleware,
    LocaleMiddleware,
    SetupCheckMiddleware,
)
from blunder_tutor.web.throttle import create_engine_throttle
from blunder_tutor.web.vite import vite_asset

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context manager for FastAPI app startup/shutdown."""

    # Startup: create work coordinator with engine pool
    coordinator: WorkCoordinator = app.state.work_coordinator
    await coordinator.start()

    # In none mode the global `settings_repo` seeds scheduler settings
    # and the locale cache from the single legacy DB. Credentials mode
    # resolves settings per-request via `get_db_path`, so `settings_repo`
    # is `None` here and scheduler settings fall back to defaults.
    settings_repo = app.state.settings_repo
    if settings_repo is not None:
        scheduler_settings = await settings_repo.get_all_settings()
        saved_locale = scheduler_settings.get("locale")
        if saved_locale:
            # AUTH_MODE=none: single `_local` key matches what the
            # middleware resolves for unauthenticated requests.
            app.state._locale_cache = {"_local": saved_locale}
    else:
        scheduler_settings = {}

    # Background scheduler + job executor are single-user in Phase 3:
    # the scheduler opens exactly one DB (the legacy one). In credentials
    # mode we skip both and revisit per-user scheduling in Phase 4.
    if app.state.scheduler is not None:
        app.state.scheduler.start(scheduler_settings)

    # Start WebSocket broadcasting task
    asyncio.create_task(app.state.connection_manager.start_broadcasting())

    if app.state.job_executor is not None:
        asyncio.create_task(app.state.job_executor.start())
    asyncio.create_task(app.state.cache_invalidator.start())

    if app.state.auth_mode == "credentials":
        await _bootstrap_auth(app)

    yield

    # Shutdown
    await app.state.cache_invalidator.stop()
    if app.state.job_executor is not None:
        await app.state.job_executor.shutdown()
    if app.state.scheduler is not None:
        app.state.scheduler.shutdown()
    await coordinator.shutdown()
    if settings_repo is not None:
        await settings_repo.close()
    if app.state.auth_service is not None:
        await app.state.auth_service.close()
    if app.state.auth_db is not None:
        await app.state.auth_db.close()


async def _bootstrap_auth(app: FastAPI) -> None:
    """Initialize `auth.sqlite3`, wire an `AuthService`, and — when no
    users exist yet — surface an invite code so an operator can finish
    first-run setup. All side effects run on the app's own event loop so
    `aiosqlite` connections are bound to the same loop as request handlers.

    Orphan-directory scan is deliberately deferred to Task 16.
    """
    auth_db_path: Path = app.state.auth_db_path
    users_dir: Path = app.state.users_dir
    auth_config = app.state.auth_config

    await initialize_auth_schema(auth_db_path)

    auth_db = AuthDb(auth_db_path)
    await auth_db.connect()
    app.state.auth_db = auth_db

    auth_service = AuthService(
        auth_db=auth_db,
        users_dir=users_dir,
        session_max_age=timedelta(seconds=auth_config.session_max_age_seconds),
        session_idle=timedelta(seconds=auth_config.session_idle_seconds),
    )
    app.state.auth_service = auth_service

    if await auth_service.user_count() == 0:
        try:
            setup_repo = SetupRepository(db=auth_db)
            invite = await setup_repo.get("invite_code")
            if invite is None:
                invite = generate_invite_code(auth_config.secret_key)
                await setup_repo.put("invite_code", invite)
            log.info("=" * 60)
            log.info("FIRST-USER SETUP: invite code required at /setup")
            log.info("Invite code: %s", invite)
            log.info("=" * 60)
        except Exception:
            # Non-fatal: a bad invite-code write shouldn't block the app
            # from booting. Operators can always re-bootstrap via the CLI
            # (Task 17).
            log.exception("Failed to generate or persist first-user invite code")


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

    templates = Jinja2Templates(directory=str(config.data.template_dir))

    # Initialize i18n
    locales_dir = Path(__file__).parent.parent.parent / "locales"
    i18n = TranslationManager(locales_dir)
    app.state.i18n = i18n

    # Register Jinja2 global for translations
    templates.env.globals["t"] = (
        lambda key, **kwargs: key
    )  # placeholder, overridden per-request
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

    # JobExecutor + BackgroundScheduler are tied to a single DB path.
    # In credentials mode each user owns their own DB, so per-user
    # scheduling is a Phase 4 concern — skip both here and the lifespan
    # guards on `is not None` keep startup clean.
    if config.auth.mode == "none":
        app.state.job_executor = JobExecutor(
            event_bus=event_bus,
            db_path=config.data.db_path,
            engine_path=config.engine_path,
            work_coordinator=work_coordinator,
        )
        app.state.scheduler = BackgroundScheduler(
            db_path=config.data.db_path,
            event_bus=event_bus,
            engine_path=config.engine_path,
        )
    else:
        app.state.job_executor = None
        app.state.scheduler = None
    app.state.settings_repo = settings

    # Auth state — `AuthDb` and `AuthService` are connected in the lifespan
    # (credentials mode only) so their aiosqlite connections live on the
    # app's own event loop.
    app.state.legacy_db_path = config.data.db_path
    app.state.auth_mode = config.auth.mode
    app.state.auth_config = config.auth
    app.state.auth_db = None
    app.state.auth_service = None

    if config.auth.mode == "credentials":
        auth_db_path = config.data.db_path.parent / "auth.sqlite3"
        users_dir = config.data.db_path.parent / "users"
        users_dir.mkdir(parents=True, exist_ok=True)
        app.state.auth_db_path = auth_db_path
        app.state.users_dir = users_dir

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

    # Add middleware (order matters: last added = first executed).
    # `AuthMiddleware` runs first so downstream middleware can read the
    # per-request `user_ctx` / `db_path` from `request.state`.
    app.add_middleware(SetupCheckMiddleware)
    app.add_middleware(DemoModeMiddleware)
    app.add_middleware(LocaleMiddleware)
    app.add_middleware(AuthMiddleware)
    app = routes.configure_router(app)
    return app


def create_app_factory() -> FastAPI:
    """Factory function for uvicorn --factory mode."""
    return create_app(config_factory(None, os.environ))
